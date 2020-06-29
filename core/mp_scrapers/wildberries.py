import re
from typing import List, Dict

from bs4 import BeautifulSoup

from .configs import WILDBERRIES_CONFIG
from core.utils.proxy_manager import ProxyManager
from core.utils.connector import Connector
from core.types import RequestBody
from core.utils.trees import Node


class WildberriesCategoryScraper:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.connector = Connector()
        self.config = WILDBERRIES_CONFIG
        self.headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        self.base_catalog_pattern = 'https:\/\/www.wildberries.ru\/catalog\/{}'

    def get_request_info(self) -> RequestBody:
        proxies = self.proxy_manager.get_proxy() if self.config.use_proxy else None
        return RequestBody(
            url=self.config.categories_url,
            method='get',
            proxies=proxies,
            headers=self.headers
        )

    def compare_result_to_db(self, parsed: Node) -> bool:
        pass

    def _parse_all_descendants(self, all_categories: List[Node], level: str = '') -> List[Node]:
        descedant_pattern = self.base_catalog_pattern.format(level + '[^\/\?]+')
        descendants = [Node(tag.text, tag['href']) for tag in all_categories if re.fullmatch(descedant_pattern,
                                                                                             tag['href'])]

        for descendant_node in descendants:
            level_start_idx = descendant_node.mp_url.rfind('/')
            new_level = descendant_node.mp_url[level_start_idx+1:] + '/'
            descendant_node.descendants.extend(self._parse_all_descendants(all_categories, level=new_level))

        return descendants

    def parse_bs_response(self, bs: BeautifulSoup) -> List[Node]:
        all_categories_pattern = self.base_catalog_pattern.format('[^\?].+')
        all_categories = bs.findAll('a', href=re.compile(all_categories_pattern))

        parsed_nodes = self._parse_all_descendants(all_categories)

        return parsed_nodes


    def update_categories(self):
        request_info = self.get_request_info()

        for bs in self.connector.send_request(request_info):
            parsed = self.parse_bs_response(bs)
            result = self.compare_result_to_db(parsed)


class WildberriesRevisionScraper:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.config = WILDBERRIES_CONFIG

    def get_requests(self):
        pass

    def parse_responses(self, responses: List[BeautifulSoup]):
        pass
