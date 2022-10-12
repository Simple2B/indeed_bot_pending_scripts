import re
from time import sleep

import gspread
from gspread.exceptions import GSpreadException
from oauth2client.service_account import ServiceAccountCredentials
import httplib2
import apiclient.discovery

from .utils import print_work_time, current_date, sorted_row_by_titles_list
from config import config as conf


class GoogleSheetsClient:
    _instance = None

    def __init__(self):
        if self._instance:
            return self._instance
        self._httpAuth = None
        self.gclient = None
        self.sheet_service = None
        self.count_added_jobs = 0

        self.sample_list_jobs = []

        self.connect()
        self._instance = self

    def connect(self):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            conf.GOOGLE_CREDS_FILE,
            [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/drive.appdata",
                "https://www.googleapis.com/auth/drive.scripts",
                "https://www.googleapis.com/auth/drive.metadata",
            ],
        )

        self._httpAuth = credentials.authorize(httplib2.Http())

        self.gclient = gspread.authorize(credentials)

        self.sheet_service = apiclient.discovery.build(
            "sheets", "v4", http=self._httpAuth
        )
        self.drive_service = apiclient.discovery.build(
            "drive", "v3", http=self._httpAuth
        )

    def find_client_sheet(self, file_name: str):
        self.connect()
        res = (
            self.drive_service.files()
            .list(
                q=f"name='{file_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' ",
                fields="files(id, name)",
            )
            .execute()
        )

        files = res.get("files")
        if files:
            file = files[0]
            return file.get("id")
        return None

    def parse_spreadsheet_id(self, spreadsheet_url):
        self.connect()
        if spreadsheet_url.startswith("https://docs.google.com"):
            spreadsheet_url = re.findall(r"/d/(.*)/edit", spreadsheet_url)[0]
        return spreadsheet_url

    def get_all_sheet_records(
        self, spreadsheet_id: str, worksheet: str, add_row_index: bool = False
    ):
        self.connect()

        spreadsheet = self.gclient.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet)
        try:
            all_records = worksheet.get_all_records()
        except GSpreadException:
            raise ValueError(
                f"Spreadsheet is not correct, please make sure all headers are unique in the {worksheet.title}"
            )

        if add_row_index:
            counter = 2
            for record in all_records:
                record["row_index"] = counter
                counter += 1

        return all_records

    @print_work_time
    def get_clients_list(self, full_name: str = "A"):
        if not full_name:
            full_name = "N/A"
        clients = self.get_all_sheet_records(
            spreadsheet_id=conf.INDEED_MAIN_SPREADSHEET_ID,
            worksheet="INDEED Master Clients",
            add_row_index=True,
        )
        clients = [
            client
            for client in clients
            if client.get("Full Name").lower() == full_name.lower()
            and client.get("Active", " ").lower() in ["true", "t"]
        ]

        return clients

    def get_spreadsheet_data(
        self, spreadsheet_id: str, range: str, as_dict: bool = True
    ):
        """
        Returns data from sheet of spreadsheet

        Args:
            spreadsheet_id (str): spreadsheet id or link
            range (str): sheet name

        Returns:
            list: [
                "All Words",
                "Exact Phrase",
                "At Least",
                "None",
                "In Title",
                "Company",
                "Jobs Type",
                "Jobs From",
                "Exclude Agencies",
                "Salary",
                "Radius",
                "Where",
                "Age",
                "Limit",
                "Sort"
            ]
        """
        self.connect()

        spreadsheet_id = self.parse_spreadsheet_id(spreadsheet_id)

        result = (
            self.sheet_service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=range,
            )
            .execute()
        )
        sleep(1)

        if as_dict:
            first_sheet_row = result.get("values")[0]
            keys = [value.lower().replace(" ", "_") for value in first_sheet_row]
            sheet_data = [dict(zip(keys, row)) for row in result.get("values")[1:]]
            return sheet_data
        return result.get("values")[1:] if result.get("values") else []

    def get_client_inputs(self, spreadsheet_id: str):
        client_inputs = self.get_all_sheet_records(
            spreadsheet_id=spreadsheet_id,
            worksheet="INDEED",
            add_row_index=True,
        )
        client_inputs = [
            client_input
            for client_input in client_inputs
            if client_input.get("Active") == "TRUE"
            and client_input.get("Jobsite") == "Indeed"
        ]

        return client_inputs

    def get_worksheet(self, spreadsheet_id: str, worksheet_name: str):
        self.connect()
        spreadsheet = self.gclient.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)

        return worksheet

    def row_values(
        self,
        row_index: int,
        spreadsheet_id: str = None,
        worksheet_name: str = None,
        worksheet=None,
    ):
        if not worksheet:
            spreadsheet = self.gclient.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
        row_values = worksheet.row_values(row_index)

        return row_values

    def add_rows(self, spreadsheet_id: str, range: str, rows: list):
        self.connect()
        self.sheet_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [rows] if type(rows[0]) != list else rows},
        ).execute()
        sleep(1)

    def add_to_sample_list_jobs(self, job_data: dict):
        self.sample_list_jobs.append(job_data)

    def save_sample_list_jobs(
        self,
        spreadsheet_id: str,
        country: str,
        add_to_main_spreadsheet: bool = False,
        client_name: str = "",
    ):
        self.connect()
        spreadsheet_id = self.parse_spreadsheet_id(spreadsheet_id)

        if not self.sample_list_jobs:
            return

        client_applications_worksheet = self.get_worksheet(
            spreadsheet_id, "Applications"
        )
        title_list_client_applications = client_applications_worksheet.row_values(1)

        rows = []
        for job_data in self.sample_list_jobs:
            row = {
                "Country": country,
                "Status": "Sample",
                "Client": client_name,
                "Jobsite": "Indeed",
            }
            row.update(job_data)
            rows.append(row)
        sorted_rows_by_client_title = [
            sorted_row_by_titles_list(row, title_list_client_applications)
            for row in rows
        ]

        self.add_rows(
            spreadsheet_id=spreadsheet_id,
            range="Applications!A1",
            rows=sorted_rows_by_client_title,
        )

        if add_to_main_spreadsheet:
            master_applications_worksheet = self.get_worksheet(
                conf.INDEED_MAIN_SPREADSHEET_ID, "Applications"
            )
            title_list_master_applications = master_applications_worksheet.row_values(1)

            sorted_rows_by_master_title = [
                sorted_row_by_titles_list(row, title_list_master_applications)
                for row in rows
            ]
            self.add_rows(
                spreadsheet_id=conf.INDEED_MAIN_SPREADSHEET_ID,
                range="Applications!A1",
                rows=sorted_rows_by_master_title,
            )
            # limit 60 requests per minute
            # We did 2 requests. To avoid error, we will pause for 2 seconds
            sleep(2)
            self.sample_list_jobs = []
            return
        # limit 60 requests per minute
        # We did 1 request1. To avoid error, we will pause for 1 seconds
        sleep(1)
        self.sample_list_jobs = []
        return


google_sheets_client = GoogleSheetsClient()
