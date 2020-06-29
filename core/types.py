from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ScraperConfigs:
    base_url: str
    base_categories_url: str
    base_catalog_url: str
    item_url: str
    revision_url: str
    use_proxy: bool


@dataclass
class RequestBody:
    url: str
    method: str
    headers: Dict[str, Any] = None
    params: Dict[str, Any] = None
