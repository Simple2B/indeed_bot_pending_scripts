from time import sleep
import json

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)

from selenium.webdriver.common.by import By

from .browser import Browser
from .utils import (
    current_date,
    custom_title_filters,
)
from .google_sheets import google_sheets_client
from .google_client import GoodleClient
from app.logger import log
from config import config as conf
from bs4 import BeautifulSoup as bs4


try:
    google_client = GoodleClient()
except ValueError:
    log(log.INFO, "Session expired, you need to renew the session")
    google_client = GoodleClient()


class IndeedBot(Browser):
    def find_jobs(self, url: str, client_inputs: str, pagination: int):
        if "filter" not in url:
            url += "filter=0&"

        try:
            new_browser = self.create_browser()
            new_browser.get(url)
        except ValueError:
            log(
                log.CRITICAL,
                "We can't generate users because bot uses broken proxies. Please replace your proxies with new ones. The bot stopped working",
            )
            return []

        # self.browser.get(url)
        sleep(3)
        try:
            soup = bs4(new_browser.page_source, "html.parser")
        except Exception:
            sleep(5)
            soup = bs4(new_browser.page_source, "html.parser")
        new_browser.quit()
        job_keys = []
        for job_key in soup.find_all("span"):
            job_key = job_key.get("id")
            if job_key is not None and "jobTitle" in job_key:
                job_key = job_key.replace("jobTitle-", "").strip()
                job_keys.append(job_key)
        pagination += int(client_inputs["display"])
        str_start = f"start={str(pagination)}&"
        next_page_url = ""
        if "start" in url:
            next_page_url = url.replace(
                f"start={str(pagination - client_inputs['display'])}&", str_start
            )
        next_page_url = url + str_start

        if len(job_keys) < (client_inputs["display"] - 1):
            next_page_url = None

        return {
            "job_keys": job_keys,
            "next_page_url": next_page_url,
            "pagination": pagination,
        }

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


# is_captcha_solved = anticaptcha.find_and_solve_captcha(browser=self.browser)
#         if is_captcha_solved:
#             # find continue btn and click
#             self.browser.find_and_click(
#                 find_by=By.XPATH,
#                 value="//button[@data-tn-element='auth-page-email-submit-button']",
#             )


class IndeedClient(Client):
    pass
