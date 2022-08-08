from datetime import datetime
from time import sleep, time

import urllib.request
from .const_value import QUERY_KEYS_MAP

from app.logger import log

import pycountry
import re


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


def cuntry_name_to_country_code(country: str):
    try:
        result = pycountry.countries.search_fuzzy(country)
    except LookupError:
        log(log.ERROR, f"Can't convert {country} to code")
        return None
    if result:
        result = result[0].alpha_2
    return result


def sorted_row_by_titles_list(row: dict, titles_list: list):
    return [row.get(title, "N/A") for title in titles_list]


def filter_by_include_words(title, list_data_in_title):
    for data in list_data_in_title:
        if data in title:
            return True
    return False


def custom_title_filters(client_inputs, job_title, job_company):
    list_none_of_these_words = client_inputs.get("none_of_these_words")
    list_at_least_words = client_inputs.get("at_least")
    exact_phrase = client_inputs.get("exact_phrase")
    from_company = client_inputs.get("from_company")
    in_title = client_inputs.get("in_title")

    if in_title:
        if not (in_title.lower() in job_title.lower()):
            log(
                log.INFO,
                f'The job title ({job_title.lower()}) doesn\'t include "In Title" ({in_title.lower()}) entered by the client, skip job',
            )
            return False

    if from_company:
        if not (from_company.lower() in job_company.lower()):
            log(
                log.INFO,
                f'The job company ({job_company}) doesn\'t include "From Company" ({from_company}) entered by the client, skip job',
            )
            return False

    if exact_phrase:
        if not (exact_phrase.lower() in job_title.lower()):
            log(
                log.INFO,
                f'The job title ({job_title}) doesn\'t include "Exact Phrase" ({exact_phrase}) entered by the client, skip job',
            )
            return False

    if list_at_least_words:
        if not filter_by_include_words(
            job_title.lower(),
            [word.lower().strip() for word in list_at_least_words.split(" ") if word],
        ):
            log(
                log.INFO,
                'The job title doesn\'t include "at least" \
                entered by the client, skip job',
            )
            return False

    if list_none_of_these_words:
        if filter_by_include_words(
            job_title.lower(),
            [
                word.lower().strip()
                for word in list_none_of_these_words.split(" ")
                if word
            ],
        ):
            log(
                log.INFO,
                'The job title includes "none of these words" \
                entered by the client, skip job',
            )
            return False
    return True


def generator_search_url(
    country_code: str,
    client_inputs: dict,
):
    url = f"https://{country_code}{'.' if country_code else ''}indeed.com/jobs?"
    if not country_code:
        country_code = "US"
        client_inputs["education"] = client_inputs.get("education_level")
    if client_inputs.get("job_language"):
        if client_inputs.get("job_language") == "English":
            client_inputs["job_language"] = "en"
        else:
            language_filter = cuntry_name_to_country_code(
                client_inputs.get("job_language")
            )
            client_inputs["job_language"] = (
                language_filter.lower() if language_filter else ""
            )
    if client_inputs.get("radius"):
        digits = re.findall(r"([\d.]*\d+)", client_inputs.get("radius"))
        client_inputs["radius"] = digits[0] if digits else "50"

    if client_inputs.get("salary_estimate") and country_code != "CA":
        client_inputs["salary_estimate"] = client_inputs.get("salary_estimate").replace(
            ".", ","
        )
    another_key_string = ""
    sc_key_string = ""
    q_key_string = ""
    for key in QUERY_KEYS_MAP:
        user_inputs_key_value = client_inputs.get(key)
        available_countries_for_key = QUERY_KEYS_MAP[key]["available_countries"]
        if (
            country_code in available_countries_for_key
            or "ALL" in available_countries_for_key
        ):
            if not user_inputs_key_value or str(user_inputs_key_value).lower() in (
                "anytime",
                "not use",
                "all",
            ):
                continue
            if QUERY_KEYS_MAP[key].get("items"):
                if not QUERY_KEYS_MAP[key]["items"].get(user_inputs_key_value):
                    log(
                        log.ERROR,
                        f"Filtering by column ({key}) is not available because the value in the row \
                        ({QUERY_KEYS_MAP[key]['items'].get(user_inputs_key_value)}) is incorrect",
                    )
                    continue
                row_value = (
                    QUERY_KEYS_MAP[key]["items"].get(user_inputs_key_value).strip()
                )
                if "sc=0bf%3" in sc_key_string:
                    if not "%2Ckf%3" in sc_key_string:
                        sc_key_string += f"%2Ckf%3Aattr({row_value})"
                    else:
                        sc_key_string += QUERY_KEYS_MAP[key]["map_key_short"].format(
                            row_value
                        )
                else:
                    if "sc=0kf%3" in sc_key_string:
                        sc_key_string += QUERY_KEYS_MAP[key]["map_key_short"].format(
                            row_value
                        )
                    else:
                        str_key = QUERY_KEYS_MAP[key]["map_key"].format(row_value)
                        sc_key_string += f"{str_key}"
                continue
            if QUERY_KEYS_MAP[key]["map_key"] == "q":
                if "q" in q_key_string:
                    q_key_string += (
                        "%20" + f"{str(user_inputs_key_value).replace(' ', '%20')}"
                    )
                else:
                    q_key_string += f"{QUERY_KEYS_MAP[key]['map_key']}={str(user_inputs_key_value).replace(' ', '%20')}"
                continue
            another_key_string += f"{QUERY_KEYS_MAP[key]['map_key']}={str(user_inputs_key_value).replace(' ', '%20')}&"

    result_url = url + q_key_string + "&" + sc_key_string + "%3B&" + another_key_string

    return result_url


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
