# import os
from operator import itemgetter
import requests

# from config import base_dir

from config import config as conf


class Proxy:
    def __init__(self) -> None:
        self.proxies = []
        self.read_proxies_from_file()

    @property
    def count_proxy(self):
        return len(self.proxies)

    def read_proxies_from_file(self):
        try:
            res = requests.get(
                f"https://proxy-store.com/api/{conf.PROXY_STOR}/{'getproxy'}/?"
            )
            list_proxy = []
            proxy_dict = res.json()
            if proxy_dict.get("status") == "ok":
                for prox_id in proxy_dict.get("list"):
                    proxy = proxy_dict["list"].get(prox_id)
                    if proxy:
                        list_proxy.append(
                            f"{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}"
                        )

            proxies = [{"proxy": proxy, "uses": 0} for proxy in list_proxy]
            self.proxies = proxies if proxies else []
        except (TypeError, ValueError, NameError):
            self.proxies = []
        # with open(os.path.join(base_dir, "proxy.txt")) as file:
        #     proxies = [{"proxy": proxy, "uses": 0} for proxy in file.read().split("\n")]
        #     self.proxies = proxies if proxies else []

    def get_proxy(self):
        self.proxies.sort(key=itemgetter("uses"))
        less_used_proxy = self.proxies[0]
        less_used_proxy["uses"] += 1
        return {
            "http": f"http://{less_used_proxy['proxy']}/",
            "https": f"http://{less_used_proxy['proxy']}/",
        }


proxy_service = Proxy()
