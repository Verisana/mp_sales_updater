from typing import List

from bs4 import BeautifulSoup

from .configs import WILDBERRIES_CONFIG
from core.utils.proxy_manager import ProxyManager


class WildberriesCategoryScraper:
    pass


class WildberriesRevisionScraper:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.config = WILDBERRIES_CONFIG

    def get_requests(self):
        pass

    def parse_responses(self, responses: List[BeautifulSoup]):
        pass
