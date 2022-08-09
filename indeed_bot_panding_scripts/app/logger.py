import logging
from datetime import datetime
from config import base_dir
import os

LOGGER_NAME = "IndeedBotLog"


class Logger(object):
    # __created_std_out = False
    log_file = bytes
    EXCEPTION = 100
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0

    def __init__(self):
        self.__log = logging.getLogger(LOGGER_NAME)
        # create formatter
        formatter = logging.Formatter("%(asctime)-15s [%(levelname)-8s] %(message)s")
        date = datetime.now().strftime("%m-%d-%Y")  # %H:%M:%S
        log_file_path = os.path.join(base_dir, "logs/")
        log_file_path = "C:\\1 TB\\Developers\\Simple 2B\\Logs\\"

        if not os.path.exists(log_file_path):
            os.makedirs(log_file_path)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        self.__log.addHandler(console_handler)

        file_handler = logging.FileHandler(
            log_file_path + "LOG " + date + ".txt", encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.__log.addHandler(file_handler)

        self.__log.setLevel(self.INFO)
        self.__methods_map = {
            self.DEBUG: self.__log.debug,
            self.INFO: self.__log.info,
            self.WARNING: self.__log.warning,
            self.ERROR: self.__log.error,
            self.CRITICAL: self.__log.critical,
            self.EXCEPTION: self.__log.exception,
        }

    def __call__(self, lvl, msg, *args, **kwargs):
        if lvl in self.__methods_map:
            self.__methods_map[lvl](msg, *args, **kwargs)
        else:
            self.__log.log(lvl, msg, *args, **kwargs)

    def set_level(self, level=None):
        if level is None:
            level = self.INFO
        self.__log.setLevel(level)


log = Logger()
