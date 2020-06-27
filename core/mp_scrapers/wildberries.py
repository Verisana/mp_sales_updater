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

    def _fill_all_descendants(self, node: Node, bs: BeautifulSoup) -> Node:
        for tag in bs.find('ul', {'data-menu-id': node.mp_id}).findAll('li'):


    def parse_bs_response(self, bs: BeautifulSoup) -> List[Node]:
        parsed_nodes = [Node(tag.text, tag['data-menu-id']) for tag in bs.find('ul', class_='topmenus').findAll('li')]

        for node in parsed_nodes:
            node.descendants.append(self._fill_all_descendants(node, bs))
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
