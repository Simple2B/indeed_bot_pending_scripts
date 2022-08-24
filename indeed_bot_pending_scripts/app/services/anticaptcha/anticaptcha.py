from time import sleep
import re
import requests
from datetime import datetime

from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from anticaptchaofficial.hcaptchaproxyless import hCaptchaProxyless
from selenium.webdriver.common.by import By

from config import config as conf
from app.services import Browser
from app.services.google_client import google_client
from app.logger import log


class AntiCaptcha:
    def __init__(self, browser=None):
        self.get_balance()
        self.browser = browser
        self.solver = hCaptchaProxyless()
        self.solver.set_verbose(1)
        self.solver.set_key(conf.ANTI_CAPTCHA_KEY)

    def get_balance(self):
        res = requests.post(
            "https://api.anti-captcha.com/getBalance",
            json={"clientKey": conf.ANTI_CAPTCHA_KEY},
        )
        data_res = res.json()
        if data_res.get("balance") <= 1:
            google_client.send_email(
                conf.SEND_MAIL_TO,
                f"Solved captcha error in pending scripts. Time: {datetime.now()}, SEVERITY: MEDIUM",
                f"Your balance on the 'https://anti-captcha.com/' is less than 1. So soon indeed bot will not be able to pass the captcha, please top up your balance",
            )

    def solve_recaptcha_anticaptcha(
        self, website_key: str, website_URL: str, useragent: str
    ):
        self.solver.set_website_url(website_URL)
        self.solver.set_website_key(website_key)
        self.solver.set_user_agent(useragent)
        g_response = self.solver.solve_and_return_solution()
        if g_response:
            return g_response
        elif g_response == 0:
            log(log.CRITICAL, f"Solved captcha error. Please check log above")
            return False
        else:
            return False

    def solve_captcha(self, captcha_iframe: WebElement, browser: Browser = None):
        if not browser:
            browser = self.browser
        captcha_src = captcha_iframe.get_attribute("src")
        site_key = re.findall(r"\bsitekey=\b(.*)&", captcha_src)[0]

        g_response = self.solve_recaptcha_anticaptcha(
            website_key=site_key,
            website_URL=browser.browser.current_url,
            useragent=browser.browser.execute_script("return navigator.userAgent;"),
        )
        if not g_response:
            raise ValueError("Captcha is not solved")

        browser.browser.execute_script(
            f" \
                const token = '{g_response}'; \
                const iframes = document.getElementsByTagName('iframe'); \
                iframes[0].setAttribute('data-hcaptcha-response', token); \
                const salt = iframes[0].getAttribute('data-hcaptcha-widget-id'); \
                document.getElementById('h-captcha-response-' + salt).innerHTML = token; \
            "
        )

    def find_and_solve_captcha(self, time: float = 3, browser: Browser = None):
        if not browser:
            browser = self.browser
        try:
            # try to find captcha element
            captcha_iframe = browser.wait_for_element(
                By.XPATH,
                "//div[contains(@class, 'pass-Captcha')]/div/iframe",
                time=time,
            )
            # solve captcha
            self.solve_captcha(captcha_iframe, browser)
            sleep(1)
            return True
        except (NoSuchElementException, TimeoutException, ValueError):
            return False
