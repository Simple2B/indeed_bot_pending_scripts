from bs4 import BeautifulSoup as bs4
import requests


class BS4Parser:
    @classmethod
    def is_not_external(cls, url):
        req = requests.get(url)
        soup = bs4(req.text, "html.parser")

        for tag_a in soup.find_all("a", href=True):
            if "/apply/linkout" in tag_a.get("href"):
                return (False, req.text)
        return (True, req.text)

    @classmethod
    def get_job_body(cls, html_data: str) -> str:
        soup = bs4(html_data, "html.parser")
        job_body = soup.find_all("div", {"data-automation": "jobAdDetails"})
        if job_body:
            return job_body[0].text
        return ""
