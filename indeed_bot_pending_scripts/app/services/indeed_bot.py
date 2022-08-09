from time import sleep
import re
import json

import requests
from requests.exceptions import ReadTimeout
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    NoAlertPresentException,
    WebDriverException,
)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from .browser import Browser
from .utils import (
    current_date,
    print_work_time,
    custom_title_filters,
)
from .google_sheets import google_sheets_client
from .google_client import GoodleClient
from .anticaptcha import anticaptcha
from app.logger import log
from .proxies import proxy_service
from config import config as conf

try:
    google_client = GoodleClient()
except ValueError:
    log(log.INFO, "Session expired, you need to renew the session")
    google_client = GoodleClient()


class IndeedBot(Browser):
    def find_jobs(self, url: str, country: str):
        response = None
        if conf.USE_PROXY:
            count_proxy_status_code_403 = 0
            for i in range(proxy_service.count_proxy):
                log(log.INFO, f"Send request #{i}")
                proxy = proxy_service.get_proxy()
                try:
                    response = requests.get(url=url, proxies=proxy, timeout=10)
                except Exception as e:
                    log(log.EXCEPTION, str(e))
                    google_client.send_email(
                        conf.SEND_MAIL_TO,
                        "Proxy error",
                        "Proxy error | Error while using proxy. \
                        Please check log files maybe we cannot connect to the proxy \
                        The bot tries to change the proxy and continue its work",
                    )
                if (
                    not response
                    and response is not None
                    and response.status_code == 403
                ):
                    count_proxy_status_code_403 += 1
                if response and response.status_code == 200:
                    log(log.INFO, f"Request #{i} succeed")
                    break

                log(log.ERROR, f"Proxy [{proxy}] doesnt work. Skip")
            if count_proxy_status_code_403 == proxy_service.count_proxy:
                log(
                    log.CRITICAL,
                    f"All proxies do not work for the country: ({country}). Please add new proxies to the proxy file or change country",
                )
                log(log.ERROR, f"Cannot load jobs")
                return []

            if not response or response.status_code != 200:
                log(log.ERROR, f"Cannot load jobs")
                return []
        else:
            log(log.INFO, f"Load jobs without proxy [USE_PROXY == False]")
            try:
                response = requests.get(url=url)
            except (ConnectionError, ReadTimeout):
                log(log.ERROR, f"Cannot connect to Indeed. Load jobs failed")
                return []

        html = response.text
        job_keys = re.findall(r"\bjobKeysWithInfo..\b(.*)'", html)
        next_page_url = None
        if job_keys:
            next_page_url = re.findall(r"\brel=\"next\" href=\"(.*)\" ", html)
            if next_page_url:
                next_page_url = (
                    re.findall(r"(.*\bindeed.com)", url)[0] + next_page_url[0]
                )

        return {"job_keys": job_keys, "next_page_url": next_page_url}

    def get_job_details_by_url(self, url):
        self.browser.execute_script(f"window.open('{url}','_blank');")
        self.switch_tab(1)

        try:
            json_string = self.wait_for_element(By.CSS_SELECTOR, "body > pre")
            json_object = json.loads(json_string.text)
            return json_object
        except (NoSuchElementException, TimeoutException) as e:
            return False
        finally:
            self.browser.close()
            self.switch_tab(0)

    def process_job(
        self,
        job_key: str,
        client_inputs: list,
        country_code: str,
    ):
        log(log.INFO, f"Start getting data of job({job_key})")

        job_url = f"https://{country_code}{'.' if country_code else ''}indeed.com/viewjob?jk={job_key}&vjs=1"

        log(log.INFO, "Load job details")
        job_details = self.get_job_details_by_url(job_url)
        if not job_details:
            log(log.INFO, "Couldn't load job details. Skip job")
            return

        job_advertiser = job_details["sicm"]["cmN"]
        if not job_details["jobTitle"] and not job_advertiser:
            log(log.ERROR, "Job title and job company didn't find. Skip job")
            return

        if not custom_title_filters(
            client_inputs, job_details["jobTitle"], job_advertiser
        ):
            return

        job_key = job_details["jobKey"]
        job_title = f"=hyperlink(\"https://{country_code}{'.' if country_code else ''}indeed.com/viewjob?jk={job_key}\",\"{job_details['jobTitle']}\")"
        job_location = job_details["jobLocationModel"]["fullFormattedLocation"]

        job_type = job_details["jtsT"]
        if not job_type:
            if client_inputs.get("jobs_type", "all") != "all":
                job_type = client_inputs.get("jobs_type")
            else:
                job_type = (
                    job_details.get("rwt") if job_details.get("rwt") else "Full-time"
                )

        job_data = {
            "All Words": client_inputs["all_words"],
            "JobId": job_key,
            "Job Title": job_title,
            "Advertiser": job_advertiser,
            "Timestamp": current_date(),
            "Job Type": job_type,
            "Location": job_location,
        }

        log(
            log.INFO,
            f"Add data job Id:({job_data.get('JobId')}) to sample list of jobs",
        )
        google_sheets_client.add_to_sample_list_jobs(job_data=job_data)
        # google_sheets_client.count_added_jobs += 1

    def create_and_save_screenshot(self, element: str = None):
        screenshot = self.create_screenshot(element)
        res = google_client.drive_save_screenshot(screenshot)
        screenshot_hyperlink = f"=hyperlink(\"https://drive.google.com/file/d/{res.get('id')}/view\",\"{res.get('filename')}\")"
        return screenshot_hyperlink


class Client:
    def __init__(
        self,
        email: str,
        password: str,
        user_name: str,
        country: str,
        sheet_row_index: int = None,
    ):
        self.email = email
        self.password = password
        self.user_name = user_name
        self.spreadsheet_url = google_sheets_client.find_client_sheet(user_name)
        self.clients_inputs = []
        self.country = country
        self.sheet_row_index = sheet_row_index

        if self.spreadsheet_url:
            try:
                self.clients_inputs = google_sheets_client.get_client_inputs(
                    spreadsheet_id=self.spreadsheet_url
                )
            except ValueError:
                log(
                    log.ERROR,
                    f"Client: {user_name} inputs table is not correct, please make sure the all columns are unique",
                )
                google_client.send_email(
                    conf.SEND_MAIL_TO,
                    "Error getting from Client inputs",
                    f"Client inputs table is not correct. Please make sure the spreadsheet of client:{user_name} follows rules and check log files \
                    The but skips the client: {user_name} continues its work on another client",
                )
                self.clients_inputs = []

        self.browser = IndeedBot()

    def __del__(self):
        self.browser.browser.quit()


class IndeedClient(Client):
    def login(self):
        # open login page
        log(log.INFO, f"Login user {self.email}")
        self.browser.open_site("https://secure.indeed.com/auth")
        sleep(3)

        # find and fill email input
        self.browser.find_and_fill(
            find_by=By.NAME, value="__email", fill_value=self.email
        )

        # close cookies modal
        try:
            self.browser.find_and_click(By.ID, "onetrust-reject-all-handler")
            sleep(1.5)
        except (NoSuchElementException, TimeoutException):
            pass

        # find continue btn and click
        self.browser.find_and_click(
            find_by=By.XPATH,
            value="//button[@data-tn-element='auth-page-email-submit-button']",
        )

        is_captcha_solved = anticaptcha.find_and_solve_captcha(browser=self.browser)
        if is_captcha_solved:
            # find continue btn and click
            self.browser.find_and_click(
                find_by=By.XPATH,
                value="//button[@data-tn-element='auth-page-email-submit-button']",
            )

        errors = self.browser.find_errors()
        if errors:
            log(log.ERROR, "Found errors on the login page. Failed login")
            log(log.ERROR, errors)
            google_client.send_email(
                conf.SEND_MAIL_TO,
                "Login Failed",
                f"Error was found on the login page when the user logged in to the site. \
                Please check log files also if client: {self.user_name} data in the table is valid \
                The bot tries to login the client:  {self.user_name} again and continue its work",
            )
            return False

        # find btn to login by password
        # it exists if user created using Google auth
        # if exists > click
        try:
            self.browser.find_and_click(
                find_by=By.ID, value="auth-page-google-password-fallback"
            )
        except (NoSuchElementException, TimeoutException) as e:
            pass

        # find and fill password input
        self.browser.find_and_fill(
            find_by=By.NAME, value="__password", fill_value=self.password
        )

        # find login btn and click
        self.browser.find_and_click(
            find_by=By.XPATH,
            value="//button[@data-tn-element='auth-page-sign-in-password-form-submit-button']",
        )

        # find error message block
        # if exists log error message and skip current client
        try:
            error_message_div = self.browser.wait_for_element(
                find_by=By.ID, value="ifl-InputFormField-errorTextId-5", time=5
            )
            error_text = error_message_div.find_element_by_class_name("css-mllman").text

            log(log.ERROR, f"Found error: {error_text}")
            return
        except (NoSuchElementException, TimeoutException):
            pass

        # sometimes captcha appear on this step
        is_captcha_solved = anticaptcha.find_and_solve_captcha(browser=self.browser)
        if is_captcha_solved:
            # find and fill password input
            self.browser.find_and_fill(
                find_by=By.NAME, value="__password", fill_value=self.password
            )

            # find login btn and click
            self.browser.find_and_click(
                find_by=By.XPATH,
                value="//button[@data-tn-element='auth-page-sign-in-password-form-submit-button']",
            )

        try:
            for i in range(1, 4):
                time_sleep = 15 * i
                two_fa_form = self.browser.wait_for_element(
                    find_by=By.ID, value="two-factor-auth-form", time=2
                )
                log(log.INFO, f"Find 2FA code [#{i}]")
                if re.findall(
                    r"\blogin\/emailtwofactorauth\b", self.browser.browser.current_url
                ):
                    sleep(8)
                    code = google_client.find_code(self.email)

                    if code:
                        code_input = two_fa_form.find_element(
                            By.ID, "verification_input"
                        )
                        code_input.send_keys(code)

                        anticaptcha.find_and_solve_captcha(browser=self.browser)

                        self.browser.find_and_click(find_by=By.ID, value="submit-code")
                    if (
                        self.browser.browser.current_url
                        == "https://secure.indeed.com/settings/account"
                    ):
                        log(log.INFO, f"2FA success {self.email}")
                        return True
                log(log.INFO, f"Wrong code. Pause {time_sleep} sec.")
                sleep(time_sleep)
            log(log.INFO, f"Login Fail {self.email}")
            return False
        except (NoSuchElementException, TimeoutException):
            pass

        if (
            self.browser.browser.current_url
            == "https://secure.indeed.com/settings/account"
        ):
            return True

        return True
