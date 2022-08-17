import pickle
import os
import base64
import re
from time import sleep
from uuid import uuid4

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from bs4 import BeautifulSoup
from email.message import EmailMessage
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from app.logger import log
from config import config as conf


class GoodleClient:
    _instance = None

    def __init__(self):
        if self._instance:
            return self._instance
        self.CLIENT_SECRET_FILE = "gmail_account.json"
        self.SCOPES = [
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.appdata",
            "https://www.googleapis.com/auth/drive.scripts",
            "https://www.googleapis.com/auth/drive.metadata",
        ]
        self.pickle_file = "token_google.pickle"

        self.drive_service = None
        self.gmail_service = None
        self.init_services()
        self._instance = self

    def init_services(self):
        cred = None

        if os.path.exists(self.pickle_file):
            with open(self.pickle_file, "rb") as token:
                cred = pickle.load(token)

        if not cred or not cred.valid:
            if cred and cred.expired and cred.refresh_token:
                try:
                    cred.refresh(Request())
                except RefreshError:
                    os.remove(self.pickle_file)
                    raise ValueError
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CLIENT_SECRET_FILE, self.SCOPES
                )
                while True:
                    try:
                        cred = flow.run_local_server()
                        break
                    except OSError:
                        sleep(5)
                        log(
                            log.CRITICAL,
                            "Please to renew the session in seek, after in indeed",
                        )

            with open(self.pickle_file, "wb") as token:
                pickle.dump(cred, token)

        try:
            self.drive_service = build("drive", "v3", credentials=cred)
        except Exception as error:
            log(log.EXCEPTION, "Unable to connect to Google Drive")
            log(log.EXCEPTION, f"{error}")
            return None

        try:
            self.gmail_service = build("gmail", "v1", credentials=cred)
        except Exception as error:
            log(log.EXCEPTION, "Unable to connect to Gmail")
            log(log.EXCEPTION, f"{error}")
            return None

    def drive_save_screenshot(self, screenshot):
        file_name = str(uuid4())
        file_metadata = {"name": file_name, "parents": [conf.GOOGLE_SCREENSHOT_FOLDER]}

        media = MediaInMemoryUpload(screenshot, mimetype="image/jpeg", resumable=True)
        file = (
            self.drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        return {"filename": file_name, "id": file.get("id")}

    def send_email(self, mail_to: str, msg_text: str, subject: str):
        try:
            message = EmailMessage()
            message.set_content(msg_text)
            message["To"] = mail_to
            message["Subject"] = subject
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}
            send_message = (
                self.gmail_service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )

        except Exception as error:
            log(log.EXCEPTION, f"Send email exception")
            log(log.EXCEPTION, f"{error}")
            return None

        return send_message

    def get_messages(self, limit: int = 5):
        # request a list of all the messages
        result = (
            self.gmail_service.users()
            .messages()
            .list(userId="me", maxResults=limit)
            .execute()
        )

        # We can also pass maxResults to get any number of emails. Like this:
        messages = result.get("messages")

        return messages

    def find_code(self, user_email):
        messages = self.get_messages(10)

        for message in messages:
            # Get the message from its id
            message_data = (
                self.gmail_service.users()
                .messages()
                .get(userId="me", id=message["id"])
                .execute()
            )

            payload = message_data["payload"]
            parts = payload.get("parts")
            if not parts:
                continue
            data = parts[0]["body"].get("data")
            if not data:
                log(log.ERROR, "Google Gmail can not find email message body")
                sleep(10)
                continue
            data = data.replace("-", "+").replace("_", "/")
            decoded_data = base64.b64decode(data)

            message_html = BeautifulSoup(decoded_data, "lxml")

            if re.findall(rf"\b{user_email}\b", str(message_html)):
                code = re.findall(r"\n(\d{6})", str(message_html))
                if code:
                    return code[0]

        return None


google_client = GoodleClient()
