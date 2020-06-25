from dataclasses import dataclass

from core.utils.connector import Connector
from core.utils.proxy_manager import ProxyManager


@dataclass
class ScraperConfigs:
    categories_url: str
    item_url: str
    revision_url: str


class BaseScraper:
    def __init__(self, connector_args, proxy_manager_args):
        self.connector = Connector(*connector_args)
        self.proxy_manager = ProxyManager(*proxy_manager_args)
        self.urls = []
        self.proxies = []
        self.responses = []