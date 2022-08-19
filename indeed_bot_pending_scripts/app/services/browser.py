from base64 import b64decode
import io


from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.keys import Keys

from .google_client import google_client
from .proxies import proxy_service
from config import config as conf
from app.logger import log

from selenium import webdriver
from seleniumwire import webdriver as wirewebdriver


class Browser:
    def __init__(self):
        # self.browser = self.create_browser()

        # self.browser.maximize_window()
        # self.is_proxy_works()
        options = ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--log-level=4")
        # oprions.add_argument("--proxy-server=%s" % PROXY)
        if conf.HIDE_BROWSER:
            options.add_argument("--headless")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])

        self.browser = webdriver.Chrome(
            executable_path=conf.CHROMEDRIVER_PATH, options=options
        )
        self.browser.maximize_window()

    def create_browser(self):
        count_idle_proxies = 0
        for i in range(proxy_service.count_proxy):
            # proxy = {
            #     "http": "http://dander0701_gmail_com:02a8c363c1@83.171.212.17:30013",
            #     "https": "http://dander0701_gmail_com:02a8c363c1@83.171.212.17:30013",
            # }
            proxy = proxy_service.get_proxy()
            proxy.update({"no_proxy": "localhost,127.0.0.1"})
            options = {"proxy": proxy}
            chrome_options = webdriver.ChromeOptions()
            # chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-logging"]
            )
            chrome_options.add_argument("--log-level=5")
            # chrome_options.add_argument("--headless")
            # chrome_options.add_argument("--ignore-certificate-errors-spki-list")
            # chrome_options.add_argument("--ignore-ssl-errors")
            chrome_options.add_argument("--headless")
            browser = wirewebdriver.Chrome(
                executable_path=conf.CHROMEDRIVER_PATH,
                options=chrome_options,
                seleniumwire_options=options,
            )
            try:
                log(log.INFO, f"Send request #{i}")
                browser.get("https://google.com/")
                return browser
            except WebDriverException:
                count_idle_proxies += 1
                log(log.ERROR, f"Proxy [{proxy}] doesnt work. Skip")
            except Exception as e:
                log(
                    log.ERROR,
                    f"An unknown error ({e}) occurred while processing this proxy: [{proxy}]. Please check the log file",
                )
        if count_idle_proxies >= proxy_service.count_proxy or not proxy_service.proxies:
            google_client.send_email(
                conf.SEND_MAIL_TO,
                "Proxy error",
                "Proxy error | Error while using proxy. \
                        Please check log files maybe we cannot connect to the proxy \
                        The bot will stope its work",
            )
            raise ValueError

    def open_site(self, url: str):
        self.browser.get(url)

    def find_and_click(self, find_by: By, value: str, time: float = 7):
        """
        Looking for an element and click on it or raise NoSuchElementException

        Args:
            find_by (By(selenium.webdriver.common.by)): attribute to find element(class, id, name, etc)
            value (str): attribute value(myclass, myid)
            time (float): time to wait element
        """

        element = self.wait_for_element(find_by, value, time)
        element.click()

    def find_and_fill(self, find_by: By, value: str, fill_value: str):
        """
        Looking for an element and fill it or raise NoSuchElementException

        Args:
            find_by (By(selenium.webdriver.common.by)): attribute to find element(class, id, name, etc)
            value (str): attribute value(myclass, myid)
            fill_value (str): value to fill an element
        """

        element = self.wait_for_element(find_by, value)
        element.send_keys(fill_value)

    def wait_for_element(self, find_by: By, value: str, time: float = 7) -> WebElement:
        """
        Waiting for element and return it if exists

        Args:
            find_by (By(selenium.webdriver.common.by)): attribute to find element(class, id, name, etc)
            value (str): attribute value(myclass, myid)
        """
        self.wait = WebDriverWait(self.browser, time)
        element = self.wait.until(EC.visibility_of_element_located((find_by, value)))

        return element

    def switch_tab(self, tab_index):
        self.browser.switch_to.window(self.browser.window_handles[tab_index])

    def find_errors(self, time: float = 3):
        error_message_block = None
        try:
            error_message_block = self.wait_for_element(
                find_by=By.XPATH,
                value="//div[contains(@class, 'css-mllman')]",
                time=time,
            )
        except (NoSuchElementException, TimeoutException):
            pass

        if not error_message_block:
            try:
                error_message_block = self.wait_for_element(
                    find_by=By.XPATH,
                    value="//span[contains(@role, 'alert')]",
                    time=1,
                )
            except (NoSuchElementException, TimeoutException):
                pass

        if error_message_block:
            error_text = error_message_block.text
            if error_text:
                return error_text
        return False

    def clear_element(self, element: WebElement):
        element.send_keys(Keys.COMMAND + "a")
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.DELETE)

    def create_screenshot(self, element=None):

        if element:
            try:
                self.browser.execute_script("arguments[0].scrollIntoView();", element)
            except Exception:
                pass
        screenshot = self.browser.get_screenshot_as_base64()
        if type(screenshot) == str:
            screenshot = io.BytesIO(b64decode(screenshot))
            screenshot = screenshot.getvalue()
        return screenshot
