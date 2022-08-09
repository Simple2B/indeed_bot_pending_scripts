from typing import Union
from datetime import datetime
from time import time, sleep

import urllib.request

from app.logger import log


def current_date():
    now = datetime.now()  # current date and time
    date_time = now.strftime("%Y-%m-%d %H:%M:%S")
    return date_time


def print_work_time(func):
    def wrap_func(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        log(log.DEBUG, f"Function {func.__name__!r} executed in {(t2-t1):.4f}s")
        return result

    return wrap_func


def str_has_exclude_word(str_to_check: str, exclude_words: Union[list, str]):
    if type(exclude_words) != list:
        exclude_words = str(exclude_words).replace(";", "").split("\n")
    for word in exclude_words:
        if str(word).strip().lower() in str_to_check.lower():
            return True
    return False


def sorted_row_by_titles_list(row: dict, titles_list: list):
    return [row.get(title, "N/A") for title in titles_list]


def checking_internet_connection():
    while True:
        try:
            urllib.request.urlopen("http://google.com")
            break
        except:
            log(
                log.ERROR,
                "Bot can't connect to the internet, sleep 5 min",
            )
            sleep(300)
            log(log.ERROR, "5 minutes have passed, continue working")
