from datetime import timedelta
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
    items_parse_frequency: timedelta
    revisions_parse_frequency: timedelta
    categories_parse_frequency: timedelta
    images_parse_frequency: timedelta
    items_per_page: int


@dataclass
class RequestBody:
    url: str
    method: str
    parsing_type: str = 'bs'
    headers: Dict[str, Any] = None
    params: Dict[str, Any] = None
