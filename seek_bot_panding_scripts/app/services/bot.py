from time import sleep
import requests

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    NoAlertPresentException,
    WebDriverException,
)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from .browser import Browser
from .utils import current_date, str_has_exclude_word
from .google_sheets import google_sheets_client
from .google_client import GoodleClient
from app.logger import log
from indeed_bot_panding_scripts.config import config as conf
from .bs4_parser import BS4Parser

try:
    google_client = GoodleClient()
except ValueError as e:
    log(log.INFO, "Session expired, you need to renew the session")
    google_client = GoodleClient()
bs4parser = BS4Parser


class Bot(Browser):
    def find_jobs(self, url: str, page: int = 1):
        response = None

        try:
            response = requests.get(url=url + f"&page={page}")
        except Exception:
            log(log.ERROR, "Cannot connect to seek. Load jobs failed")
            return {}

        jobs = response.json()

        return {"jobs": jobs["data"], "next_page": page + 1 if jobs["data"] else None}

    def process_job(
        self,
        job_data: dict,
        client_inputs: list,
    ):

        job_id = job_data.get("id")
        log(log.INFO, f"Process getting data of job {job_id}")

        job_url = f"https://www.seek.com.au/job/{job_id}"

        job_advertiser = job_data.get("companyName")
        if not job_advertiser:
            job_advertiser = job_data.get("advertiser").get("description")
        job_title = f"=hyperlink(\"{job_url}\",\"{job_data.get('title')}\")"
        job_location = job_data.get("location")
        job_type = job_data.get("workType")
        job_classification = job_data.get("classification").get("description")

        job_detail = {
            "Country": client_inputs["country"],
            "Keyword": client_inputs["keyword"],
            "Job Title": job_title,
            "Advertiser": job_advertiser,
            "Timestamp": current_date(),
            "Location": job_location,
            "Classification": job_classification,
            "Type": job_type,
            "JobID": job_id,
            "Status": "N/A",
            "Jobsite": "SEEK",
        }

        tuple_job_data = bs4parser.is_not_external(job_url)

        job_body = bs4parser.get_job_body(tuple_job_data[1])
        data_to_check = [
            {
                "str": job_data["title"],
                "excluded_words": client_inputs["title_exclude"],
                "result": False,
            },
            {
                "str": job_data["title"],
                "excluded_words": client_inputs["title_include"],
                "result": True,
            },
            {
                "str": job_detail["Location"],
                "excluded_words": client_inputs["location_exclude"],
                "result": False,
            },
            {
                "str": job_detail["Classification"],
                "excluded_words": client_inputs["classification_exclude"],
                "result": False,
            },
            {
                "str": job_detail["Type"],
                "excluded_words": client_inputs["type_exclude"],
                "result": False,
            },
            {
                "str": job_body,
                "excluded_words": client_inputs["body_exclude"],
                "result": False,
            },
            {
                "str": job_body,
                "excluded_words": client_inputs["body_include"],
                "result": True,
            },
            {
                "str": job_detail["Advertiser"],
                "excluded_words": client_inputs["advertiser_exclude"],
                "result": False,
            },
        ]

        for data in data_to_check:
            if not data["excluded_words"]:
                continue
            if (
                not str_has_exclude_word(data["str"], data["excluded_words"])
                == data["result"]
            ):
                log(
                    log.ERROR,
                    f"Job data: [{data['str']}] has not include/exclude: [{data['excluded_words']}], Skip job",
                )
                return

        log(log.INFO, "Job add to Sample list")
        job_detail["Status"] = "Sample"
        google_sheets_client.add_job_to_save_list(job_data=job_detail)

    def create_and_save_screenshot(self, element: str = None):
        screenshot = self.create_screenshot(element)
        if screenshot == "N/A":
            return "N/A"
        res = google_client.drive_save_screenshot(screenshot)
        screenshot_hyperlink = (
            f"=hyperlink(\"https://drive.google.com/file/d/{res.get('id')}"
            f'/view","{res.get("filename")}")'
        )
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
            self.clients_inputs = google_sheets_client.get_client_inputs(
                spreadsheet_id=self.spreadsheet_url
            )

        self.browser = Bot()

    def __del__(self):
        self.browser.browser.quit()


class SeekClient(Client):
    def login(self):
        # open login page
        log(log.INFO, f"Login user {self.email}")
        try:
            self.browser.open_site("https://www.seek.com.au/oauth/login/?returnUrl=%2F")
        except WebDriverException:
            sleep(3)
            try:
                if not self.browser.browser.current_url.startswith(
                    "https://login.seek.com/login"
                ):
                    log(
                        log.ERROR,
                        f"Faild login, url :{self.browser.browser.current_url}",
                    )
                    return False
            except WebDriverException:
                log(log.ERROR, "Page load error")
                return False
        sleep(3)

        # find and fill email input
        self.browser.find_and_fill(
            find_by=By.ID, value="emailAddress", fill_value=self.email
        )

        self.browser.find_and_fill(
            find_by=By.ID, value="password", fill_value=self.password
        )

        self.browser.find_and_click(By.XPATH, "//button[@type='submit']")

        try:
            self.browser.wait_for_url("https://www.seek.com.au/", time=20)
        except (TimeoutException, WebDriverException):
            return False
            # log and send email

        error = None
        try:
            error_block = self.browser.wait_for_element(
                By.XPATH, "//*[@xmlns and @aria-hidden]/../../../div/div/div/span", 3
            )
            error = error_block.text
        except (NoSuchElementException, TimeoutException, WebDriverException):
            pass

        if error:
            log(log.ERROR, error)
            google_client.send_email(
                conf.SEND_MAIL_TO,
                "Login Failed",
                f"Error was found on the login page when the user logged in to the site. \
                Please check log files also if client: {self.user_name} data in the table is valid \
                The bot tries to login the client:  {self.user_name} again and continue its work",
            )
            return False
        return True
