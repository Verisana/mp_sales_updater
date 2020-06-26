from typing import List, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.utils.proxy_manager import ProxyManager
from core.utils.connector import Connector


@dataclass
class ScraperConfigs:
    categories_url: str
    item_url: str
    revision_url: str
    use_proxy: bool
    simultaneous_conn_limit: int


@dataclass
class RequestBody:
    urls: List[str]
    proxies: List[str]
    headers: List[Dict[str, str]]
    methods: List[str]
    params: List[Dict[str, Any]]


class BaseScraper(ABC):
    @property
    @abstractmethod
    def proxy_manager(self) -> ProxyManager:
        ...

    @property
    @abstractmethod
    def connector(self) -> Connector:
        ...

    @property
    @abstractmethod


    @abstractmethod
    def fetch_data(self) -> bool:
        """Send prepared requests through connector"""
        pass

    @abstractmethod
    def get_data(self) -> List[Dict[str, Any]]:
        """Retreive received data to save in DB"""
        pass

    @abstractmethod
    def parse_responses(self) -> :
        """Parse all responses"""
        pass

    @abstractmethod
    def empty_data(self):
        pass