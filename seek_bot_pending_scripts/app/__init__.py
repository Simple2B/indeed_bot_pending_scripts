import tkinter as tk
from tkinter import simpledialog
from datetime import datetime

from app.services.utils import checking_internet_connection


from app.services import (
    google_sheets_client,
    GoodleClient,
    SeekClient,
)
from app.logger import log
from config import config as conf

TK_ROOT = None
if not conf.TESTING:
    TK_ROOT = tk.Tk()
    TK_ROOT.withdraw()

google_client = GoodleClient()


QUERY_KEYS_MAP = {
    "keyword": "keywords",
    "classification": "classification",
    "location": "where",
    "type": "worktype",
    "min": "salaryrange",
    "max": "salaryrange",
    "listed": "daterange",
    "sort_by": "sortmode",
}

batch = None


def generate_clients():
    global batch

    batch_msg = "Enter Full name of client"
    while True:
        if not batch:
            batch = "A"
            if not conf.TESTING:
                batch = simpledialog.askstring(
                    title="Batch",
                    prompt=batch_msg,
                )
        client_data = google_sheets_client.get_clients_list(full_name=batch)
        if len(client_data) > 1:
            log(
                log.INFO,
                f"The bot found several clients with this Full Name: {batch} .Bot will processing just first client.",
            )
        if client_data:
            client_data = client_data[0]
            break
        batch = None
        batch_msg = "Clients not found. Please use another Full name"

    log(
        log.INFO,
        f"Process Client: {client_data['Full Name']}",
    )

    REQUIRED_FIELDS = ["Full Name", "Email", "Password"]
    has_required_fields = True
    for field in REQUIRED_FIELDS:
        if not client_data.get(field):
            log(log.ERROR, f"Client has not data in '{field}' cell. Skip client")
            google_client.send_email(
                conf.SEND_MAIL_TO,
                "Error reading client data",
                f"Client has not data in '{field}' cell. Skip client. \
                Check the spreadsheet of clients. One of the clients does \
                not have a filled field: {field} \
                The bot continues working by reading another client data",
            )
            has_required_fields = False
            break

    if not has_required_fields:
        return
    spread_sheet_id = google_sheets_client.find_client_sheet(client_data["Full Name"])
    if not spread_sheet_id:
        log(
            log.ERROR,
            f"Client {client_data['Full Name']} spreadsheet file not found. Skip client",
        )
        google_client.send_email(
            conf.SEND_MAIL_TO,
            "Error in client data",
            f"Client {client_data['Full Name']} spreadsheet file not found. Skip client \
            The bot did not find spreadsheet file of {client_data['Full Name']}. \
            Please check whether the spreadsheet file exists and whether the client({client_data['Full Name']}) has this table \
            The bot continues working by reading another client data",
        )
        return

    client = SeekClient(
        email=client_data["Email"],
        password=client_data["Password"],
        user_name=client_data["Full Name"],
        country=client_data["Country"],
        sheet_row_index=client_data["row_index"],
    )
    return client


def run_script():
    client = generate_clients()
    if not client:
        log(
            log.CRITICAL,
            "Client data is bad. The bot cannot process client data. The bot'll try restart",
        )
        return
    # if client_status is True, client has some problems we will skip the client
    client_status = None
    if not client.spreadsheet_url:
        log(log.ERROR, f"User {client.email} has not own spreadsheet")
        return
    for client_inputs in client.clients_inputs:
        log(log.INFO, f"Process client inputs: {client_inputs}")
        count_jobs = 0
        client_inputs = {
            key.lower().replace(" ", "_"): client_inputs[key] for key in client_inputs
        }

        if client_inputs["active"].lower() == "false":
            log(
                log.ERROR,
                "Client inputs in not Active. Skip inputs",
            )
            continue

        total_results = client_inputs.get("total_results")

        url = "https://www.seek.com.au/api/chalice-search/search?salarytype=annual"

        for key in QUERY_KEYS_MAP:
            user_inputs_key_value = client_inputs.get(key)
            if key == "min":
                url += f"&salaryrange={client_inputs.get('min')}-{client_inputs.get('max')}"

            elif user_inputs_key_value:
                url += f"&{QUERY_KEYS_MAP[key]}={str(user_inputs_key_value).replace(' ', '%20')}"

        log(log.INFO, f"Load Jobs [{url}]")
        try:
            jobs = client.browser.find_jobs(url, 1)

            if not jobs:
                log(log.INFO, "Jobs are not loaded. Skip client inputs")
                continue

            jobs_count = len(jobs.get("jobs"))

            log(log.INFO, f"Loaded {jobs_count} jobs")
            while jobs["jobs"]:
                log(log.INFO, "Start process loaded jobs")

                # process loaded jobs
                if jobs.get("jobs"):
                    for job_data in jobs.get("jobs"):

                        try:
                            client_status = client.browser.process_job(
                                client_inputs=client_inputs,
                                job_data=job_data,
                            )
                            count_jobs += 1
                            if count_jobs == (
                                int(total_results) if total_results else 500
                            ):
                                log(
                                    log.INFO,
                                    "The count of found jobs reached client input total result. Skip client inputs",
                                )
                                jobs["jobs"] = []
                                break

                        except Exception as e:
                            log(
                                log.ERROR,
                                f"Process job {job_data.get('id')} error",
                            )
                            log(log.ERROR, e)
                            log(log.ERROR, "-------------------------")
                            checking_internet_connection()
                            google_client.send_email(
                                conf.SEND_MAIL_TO,
                                "Process gatting data of job Error",
                                f"An unknown error occurred while gatting data of job_id: {job_data.get('id')} for client: {client.user_name}. \
                                Please check the log file. The bot continues working by gatting data for another job",
                            )
                        if client_status:
                            log(log.INFO, "Start process to change Client")
                            break
                if client_status:
                    break
                log(log.INFO, "Save job list")
                checking_internet_connection()
                google_sheets_client.save_job_list(
                    spreadsheet_id=client.spreadsheet_url,
                    add_to_main_spreadsheet=True,
                    client_name=client.user_name,
                )

                log(log.INFO, "Process loaded jobs ended")

                if jobs.get("next_page") and count_jobs != total_results:
                    log(log.INFO, "Load Jobs(next page)")

                    jobs = client.browser.find_jobs(url, jobs.get("next_page"))
                    log(log.INFO, f"Try load jobs")
                    if not jobs.get("jobs"):
                        break
                    jobs_count = len(jobs.get("jobs"))
                    log(log.INFO, f"Loaded {jobs_count} jobs")
                else:
                    break

            if client_status:
                break
        finally:
            checking_internet_connection()
    return True


def main():
    log(log.INFO, f"------- Start {datetime.now()} -------")
    if not conf.TESTING:
        try:
            while True:
                if run_script():
                    log(
                        log.INFO,
                        f"Process client was successful now you can see all sample jobs",
                    )
                    break
        except Exception as e:
            google_client.send_email(
                conf.SEND_MAIL_TO,
                "Run script error",
                "The problem occurred while launching the Bot. \
                Please check the log file \
                The bot tries to restart in automatic mode",
            )
            log(
                log.EXCEPTION,
                f"Run script error {str(e.args[0]) if e.args else str(e)}",
            )
    else:
        while True:
            if run_script():
                log(
                    log.INFO,
                    f"Process client was successful now you can see all sample jobs",
                )
                break

    log(log.INFO, f"------- End Work {datetime.now()} -------")


main()
