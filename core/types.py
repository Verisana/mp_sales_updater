from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ScraperConfigs:
    base_url: str
    base_categories_url: str
    base_catalog_url: str
    items_api_url: str
    individual_item_url: str
    seller_url: str
    revision_url: str
    bulk_item_step: int
    use_proxy: bool


@dataclass
class RequestBody:
    url: str
    method: str
    parsing_type: str = 'bs'
    headers: Dict[str, Any] = None
    params: Dict[str, Any] = None
