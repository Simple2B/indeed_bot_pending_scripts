from base64 import b64decode
import io
from time import sleep

from selenium import webdriver


from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException,
)
from selenium.webdriver.common.keys import Keys

from config import config as conf
from app.logger import log


class Browser:
    def __init__(self):
        options = ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        if conf.HIDE_BROWSER:
            options.add_argument("--headless")
        # options.add_argument(f"user-agent={UserAgent().random}")

        self.browser = webdriver.Chrome(
            executable_path=conf.CHROMEDRIVER_PATH, options=options
        )
        self.browser.maximize_window()

    def open_site(self, url: str):
        try:
            self.browser.get(url)
        except Exception:
            sleep(3)
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
        try:
            element.click()
        except ElementClickInterceptedException:
            self.browser.execute_script("arguments[0].click();", element)

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

    def wait_for_url(self, url: str, time: int = 10):
        self.wait = WebDriverWait(self.browser, time)
        self.wait.until(lambda browser: browser.current_url == url)

    def switch_tab(self, tab_index):
        self.browser.switch_to.window(self.browser.window_handles[tab_index])

    def find_errors(self, time: float = 3):
        error_message_blocks = None
        try:
            error_message_blocks = self.browser.find_elements(
                by=By.XPATH,
                value="//*[@id='errorPanel']/../../div[2]/ul/li",
            )
        except (NoSuchElementException, TimeoutException, WebDriverException):
            pass

        if error_message_blocks:
            errors = []
            for error_block in error_message_blocks:
                error_message_span = error_block.find_element(By.XPATH, ".//span")
                errors.append(error_message_span.text)

            return " | ".join(errors)
        return False

    def clear_element(self, element: WebElement):
        element.send_keys(Keys.COMMAND + "a")
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.DELETE)

    def create_screenshot(self, element=None):
        try:
            if element:
                self.browser.execute_script("arguments[0].scrollIntoView();", element)
            screenshot = self.browser.get_screenshot_as_base64()
        except WebDriverException:
            log(log.ERROR, "Screenshot create error. Skip")
            return "N/A"

        if type(screenshot) == str:
            screenshot = io.BytesIO(b64decode(screenshot))
            screenshot = screenshot.getvalue()
        return screenshot
