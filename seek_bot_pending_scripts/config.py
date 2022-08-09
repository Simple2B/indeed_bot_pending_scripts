import os
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(base_dir, ".env"))


class Config:
    TESTING = os.environ.get("TESTING", "false").lower() in ("true", "1", "t")

    GOOGLE_CREDS_FILE = os.path.join(base_dir, "service_account.json")
    SEEK_MAIN_SPREADSHEET_ID = os.environ.get("SEEK_MAIN_SPREADSHEET_ID")

    CHROMEDRIVER_PATH = os.path.join(base_dir, "drivers", "chromedriver.exe")

    GOOGLE_SCREENSHOT_FOLDER = os.environ.get("GOOGLE_SCREENSHOT_FOLDER")

    SEND_MAIL_TO = os.environ.get("SEND_MAIL_TO")

    LOOP_ENABLED = os.environ.get("LOOP_ENABLED").lower() in ("true", "1", "t")
    LOOP_PAUSE_MIN = float(os.environ.get("LOOP_PAUSE_MIN")) * 60

    HIDE_BROWSER = os.environ.get("HIDE_BROWSER", "false").lower() in ("true", "1", "t")


config = Config()
