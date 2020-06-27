from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ScraperConfigs:
    categories_url: str
    item_url: str
    revision_url: str
    use_proxy: bool


@dataclass
class RequestBody:
    url: str
    method: str
    proxies: Dict[str, str] = None
    headers: Dict[str, Any] = None
    params: Dict[str, Any] = None
