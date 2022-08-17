import os
import pathlib
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(base_dir, ".env"))


class Config:
    TESTING = os.environ.get("TESTING", "false").lower() in ("true", "1", "t")

    GOOGLE_CREDS_FILE = os.path.join(base_dir, "service_account.json")
    INDEED_MAIN_SPREADSHEET_ID = os.environ.get("INDEED_MAIN_SPREADSHEET_ID")

    GECKODRIVER_PATH = os.path.join(base_dir, "drivers", "geckodriver.exe")
    CHROMEDRIVER_PATH = os.path.join(base_dir, "drivers", "chromedriver.exe")

    ANTI_CAPTCHA_KEY = os.environ.get("ANTI_CAPTCHA_KEY")
    GOOGLE_SCREENSHOT_FOLDER = os.environ.get("GOOGLE_SCREENSHOT_FOLDER")

    USE_PROXY = os.environ.get("USE_PROXY", "false").lower() in ("true", "1", "t")

    SEND_MAIL_TO = os.environ.get("SEND_MAIL_TO")

    LOOP_ENABLED = os.environ.get("LOOP_ENABLED").lower() in ("true", "1", "t")
    LOOP_PAUSE_MIN = float(os.environ.get("LOOP_PAUSE_MIN")) * 60

    HIDE_BROWSER = os.environ.get("HIDE_BROWSER", "false").lower() in ("true", "1", "t")

    PROXY_STOR = os.environ.get("PROXY_STOR", "")


config = Config()
