from base64 import b64decode
import io

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.keys import Keys

from indeed_bot_panding_scripts.config import config as conf


class Browser:
    def __init__(self):
        options = ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        if conf.HIDE_BROWSER:
            options.add_argument("--headless")
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])

        self.browser = webdriver.Chrome(
            executable_path=conf.CHROMEDRIVER_PATH, options=options
        )
        self.browser.maximize_window()

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
