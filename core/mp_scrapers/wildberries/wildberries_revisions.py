from typing import List

from bs4 import BeautifulSoup

from core.mp_scrapers.configs import WILDBERRIES_CONFIG
from core.utils.proxy_manager import ProxyManager


class WildberriesRevisionScraper:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.config = WILDBERRIES_CONFIG

    def get_requests(self):
        pass

    def update_items(self, responses: List[BeautifulSoup]):
        pass
