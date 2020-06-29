import re
from typing import List, Dict, Any

from bs4 import BeautifulSoup
from bs4.element import Tag
from mptt.querysets import TreeQuerySet

from .configs import WILDBERRIES_CONFIG
from core.utils.proxy_manager import ProxyManager
from core.utils.connector import Connector
from core.types import RequestBody
from core.utils.trees import Node
from core.models import Marketplace, MarketplaceScheme, ItemCategory


class WildberriesCategoryScraper:
    def __init__(self):
        self.config = WILDBERRIES_CONFIG
        self.connector = Connector(use_proxy=self.config.use_proxy)
        self.all_categories_headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        self.base_catalog_pattern = 'https:\/\/www.wildberries.ru\/catalog\/{}'
        self.mp_source_id = self._get_mp_wb_id()

    def _get_mp_wb_id(self) -> int:
        scheme_qs = MarketplaceScheme.objects.get_or_create(name='FBM')[0]
        mp_wildberries, is_created = Marketplace.objects.get_or_create(name='Wildberries')
        if is_created:
            mp_wildberries.working_schemes.add(scheme_qs)
            mp_wildberries.save()
        return mp_wildberries.id

    def _parse_all_descendants(self, nodes: List[Node], level=0) -> List[Node]:
        for i, node in enumerate(nodes):
            # Для отладки
            if level in [0, 1, 2]:
                import time
                import datetime
                hour = datetime.datetime.fromtimestamp(time.time()).hour
                minute = datetime.datetime.fromtimestamp(time.time()).minute
                second = datetime.datetime.fromtimestamp(time.time()).second
                if level == 0:
                    print(f'{i+1}/{len(nodes)} - {node.name}, time: {hour:00.0f}:{minute:00.0f}:{second:00.0f}, '
                          f'level {level}')
                elif level == 1:
                    print(f'\t{i+1}/{len(nodes)} - {node.name}, time: {hour:00.0f}:{minute:00.0f}:{second:00.0f}, '
                          f'level {level}')
                elif level == 2:
                    print(f'\t\t{i+1}/{len(nodes)} - {node.name}, time: {hour:00.0f}:{minute:00.0f}:{second:00.0f}, '
                          f'level {level}')
            # Прям до сюда

            descendant_request = self.get_request_info(node.mp_url)
            descendants_bs, is_captcha = self.connector.get_page(descendant_request)

            if level == 0:
                try:
                    all_items = descendants_bs.find('ul', class_='maincatalog-list-2').findAll('li')
                except AttributeError:
                    all_items = descendants_bs.find('ul', class_='maincatalog-list-1').findAll('li')

                for item in all_items:
                    node.descendants.append(Node(item.text, self.config.base_url + item.find('a')['href']))
            else:
                all_items = descendants_bs.find('div', class_='catalog-sidebar').findAll('li')

                is_descendants_started = False
                for item in all_items:
                    try:
                        item_class = item['class']
                    except KeyError:
                        item_class = []
                    if 'hasnochild' in item_class:
                        is_descendants_started = True
                        continue
                    if is_descendants_started:
                        node.descendants.append(Node(item.text, self.config.base_url + item.find('a')['href']))

            self._parse_all_descendants(node.descendants, level+1)
        return nodes

    def _check_root_matching(self, tag: Tag) -> bool:
        """
        :param tag: Tag - tag to checl
        :return:
        1. Choose only 'li'
        2. We need only two tags to exclude premium/travels etc. tags
        3. Certain class names to include
        4. Exclude not root links. For example: .../catalog/detyam/shkola
        """
        return tag.name == 'li' and \
               len(tag['class']) == 2 and \
               ' '.join(tag['class']) == 'topmenus-item j-parallax-back-layer-item' and \
               re.fullmatch(self.base_catalog_pattern.format('[^\/\?]+'), tag.find('a')['href'])

    def _parse_bs_response(self, bs: BeautifulSoup) -> List[Node]:
        root_node_tags = bs.find('ul', class_='topmenus').findAll(self._check_root_matching)

        root_nodes = []
        for tag in root_node_tags:
            new_node = Node(tag.text, tag.find('a')['href'], tag['data-menu-id'])
            root_nodes.append(new_node)
        return self._parse_all_descendants(root_nodes)

    def _check_db_consistency(self):
        pass

    def _save_results_in_db(self, parsed_nodes: List[Node], parent: TreeQuerySet = None) -> bool:
        for parsed_node in parsed_nodes:
            if parent is not None:
                category, is_created = ItemCategory.objects.get_or_create(name=parsed_node.name,
                                                                          mp_source_id=self.mp_source_id,
                                                                          parent=parent)
            else:
                category, is_created = ItemCategory.objects.get_or_create(name=parsed_node.name,
                                                                          mp_source_id=self.mp_source_id,
                                                                          level=0)
            parsed_node.db_id = category.id
            self._save_results_in_db(parsed_node.descendants, parent=category)
        return True

    def get_request_info(self, url: str, headers: Dict[str, Any] = None) -> RequestBody:
        return RequestBody(
                    url=url,
                    method='get',
                    headers=headers)

    def update_categories(self):
        all_catalog_request = self.get_request_info(self.config.base_categories_url, self.all_categories_headers)
        bs, is_captcha = self.connector.get_page(all_catalog_request)

        import time
        import pickle
        s = time.time()
        parsed_nodes = self._parse_bs_response(bs)
        # parsed_nodes = pickle.load(open('root_nodes.p', 'rb'))
        e = time.time() - s
        print(f'Elapsed {e:0.0f} seconds')
        with open('parsed_nodes.p', 'w') as f:
            pickle.dump(parsed_nodes, f)
        result = self._save_results_in_db(parsed_nodes)
        self._check_db_consistency()


class WildberriesRevisionScraper:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.config = WILDBERRIES_CONFIG

    def get_requests(self):
        pass

    def update_items(self, responses: List[BeautifulSoup]):
        pass
