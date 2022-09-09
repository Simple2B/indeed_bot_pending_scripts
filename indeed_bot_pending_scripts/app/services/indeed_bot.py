from time import sleep
import json
from datetime import datetime

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    JavascriptException,
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

        for _ in range(3):
            try:
                new_browser = self.browser
                sleep(2)
                new_browser.get(url)
                break
            except (WebDriverException):
                log(
                    log.ERROR,
                    "Error: The bot can't load the jobs page. It tries again",
                )
                sleep(3)
        else:
            return []

        sleep(3)
        try:
            soup = bs4(new_browser.page_source, "html.parser")
        except Exception:
            sleep(5)
            soup = bs4(new_browser.page_source, "html.parser")
        # new_browser.quit()
        job_keys = []
        list_jobs = soup.find_all("td", {"class", "resultContent"})
        for job in list_jobs:
            log(log.INFO, f"Start getting data of job")
            job_data = {}
            job_location: list = job.find_all("div", {"class", "companyLocation"})
            job_advertiser: list = job.find_all("span", {"class", "companyName"})
            job_title_and_id: list = job.select(".resultContent span[title]")
            job_type: list = job.find_all("div", {"class", "attribute_snippet"})
            try:
                jon_title: str = job_title_and_id[0].text
                job_id: str = (
                    job_title_and_id[0].get("id").replace("jobTitle-", "").strip()
                )
                job_data["job_location"] = (
                    job_location[0].text
                    if job_location
                    else "Location not found on the site page"
                )
                job_data["job_advertiser"] = (
                    job_advertiser[0].text if job_advertiser else ""
                )
                job_data["job_title"] = jon_title
                job_data["job_id"] = job_id
                job_data["job_type"] = (
                    [
                        div.text
                        for div in job_type
                        if div.svg.get("aria-label") == "Job type"
                    ][0]
                    if job_type
                    else "Full-time"
                )
            except (IndexError, AttributeError, ValueError):
                log(log.ERROR, "Couldn't load job details. Skip job")
            else:
                job_keys.append(job_data)

        pagination += int(client_inputs["display"])
        str_start = f"start={str(pagination)}&"
        next_page_url = ""
        if "start" in url:
            next_page_url = url.replace(
                f"start={str(pagination - client_inputs['display'])}&", str_start
            )
        else:
            next_page_url = url + str_start

        pagination_next_page = soup.find_all(
            "a", {"data-testid": "pagination-page-next"}
        )
        pagination_next_page_another = soup.find_all("span", {"class": "np"})
        if not pagination_next_page and (
            not pagination_next_page_another
            or ("start" in url and len(pagination_next_page_another) == 1)
        ):
            next_page_url = None

        return {
            "job_keys": job_keys,
            "next_page_url": next_page_url,
            "pagination": pagination,
        }

    def process_job(
        self,
        job_data: str,
        client_inputs: list,
        country_code: str,
    ):

        job_advertiser = job_data.get("job_advertiser")
        job_title = job_data.get("job_title")
        job_location = job_data.get("job_location")
        job_type = job_data.get("job_type")
        job_id = job_data.get("job_id")

        if not job_title and not job_advertiser:
            log(log.ERROR, "Job title and job company didn't find. Skip job")
            return

        if not custom_title_filters(client_inputs, job_title, job_advertiser):
            return

        job_title = f"=hyperlink(\"https://{country_code}{'.' if country_code else ''}indeed.com/viewjob?jk={job_id}\",\"{job_title}\")"

        pro_job_data = {
            "All Words": client_inputs["all_words"],
            "JobId": job_id,
            "Job Title": job_title,
            "Advertiser": job_advertiser,
            "Timestamp": current_date(),
            "Job Type": job_type,
            "Location": job_location,
        }

        log(
            log.INFO,
            f"Add data job Id:({job_id}) to sample list of jobs",
        )
        google_sheets_client.add_to_sample_list_jobs(job_data=pro_job_data)
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
                    f"Error getting from Client inputs pending scripts. Time: {datetime.now()}, SEVERITY: HIGH",
                    f"Client inputs table is not correct. Please make sure the spreadsheet of client:{user_name} follows rules and check log files \n"
                    f"The bot stop working",
                )
                self.clients_inputs = []

        self.browser = IndeedBot()

    def __del__(self):
        if self.browser.browser is not None:
            self.browser.browser.quit()


# is_captcha_solved = anticaptcha.find_and_solve_captcha(browser=self.browser)
#         if is_captcha_solved:
#             # find continue btn and click
#             self.browser.find_and_click(
#                 find_by=By.XPATH,
#                 value="//button[@data-tn-element='auth-page-email-submit-button']",
#             )


class IndeedClient(Client):
    pass
