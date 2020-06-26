from typing import List

from bs4 import BeautifulSoup

from .base import BaseScraper
from .configs import WILDBERRIES_CONFIG
from core.utils.proxy_manager import ProxyManager



class WildberriesCategoryScraper(BaseScraper):



class WildberriesRevisionScraper(BaseScraper):
    def __init__(self):
        self._proxy_manager = ProxyManager()
        self.config = WILDBERRIES_CONFIG

    @property
    def proxy_manager(self):
        return self._proxy_manager

    def get_requests(self):
        pass

    def parse_responses(self, responses: List[BeautifulSoup]):
        pass
