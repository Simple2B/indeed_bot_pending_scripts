import os
from operator import itemgetter

from indeed_bot_panding_scripts.config import base_dir


class Proxy:
    def __init__(self) -> None:
        self.proxies = []
        self.read_proxies_from_file()

    @property
    def count_proxy(self):
        return len(self.proxies)

    def read_proxies_from_file(self):
        with open(os.path.join(base_dir, "proxy.txt")) as file:
            proxies = [{"proxy": proxy, "uses": 0} for proxy in file.read().split("\n")]
            self.proxies = proxies if proxies else []

    def get_proxy(self):
        self.proxies.sort(key=itemgetter("uses"))
        less_used_proxy = self.proxies[0]
        less_used_proxy["uses"] += 1
        return {
            "http": f"http://{less_used_proxy['proxy']}/",
            "https": f"http://{less_used_proxy['proxy']}/",
        }


proxy_service = Proxy()
