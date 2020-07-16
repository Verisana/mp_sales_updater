import re
import pickle
from typing import List

from bs4 import BeautifulSoup
from bs4.element import Tag
from mptt.querysets import TreeQuerySet

from core.types import RequestBody
from core.utils.trees import Node
from core.models import ItemCategory
from core.mp_scrapers.wildberries.wildberries_base import WildberriesBaseScraper


class WildberriesCategoryScraper(WildberriesBaseScraper):
    def __init__(self):
        self.all_categories_headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/83.0.4103.116 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        self.base_catalog_pattern = 'https://www.wildberries.ru/catalog/{}'

    def update_from_mp(self) -> None:
        bs, is_captcha, _ = self.connector.get_page(RequestBody(self.config.base_categories_url, 'get',
                                                                headers=self.all_categories_headers))
        parsed_nodes = self._parse_bs_response(bs)
        with open('parsed_nodes.p', 'wb') as f:
            pickle.dump(parsed_nodes, f)

        self._check_db_consistency()

    def update_from_file(self, load_file: str):
        parsed_nodes = pickle.load(open(load_file, 'rb'))
        self._save_all_results_in_db(parsed_nodes)
        self._check_db_consistency()

    def _parse_bs_response(self, bs: BeautifulSoup) -> List[Node]:
        root_node_tags = bs.find('ul', class_='topmenus').findAll(self._check_root_matching)

        root_nodes = []
        for tag in root_node_tags:
            name, url = tag.text, tag.find('a')['href']
            new_node = Node(name, url, parent=None)
            category, _ = ItemCategory.objects.get_or_create(name=new_node.name, mp_category_url=new_node.mp_url,
                                                             mp_source=self.mp_source, level=0)
            new_node.db_id = category.id
            root_nodes.append(new_node)

        return self._parse_all_descendants(root_nodes)

    def _check_root_matching(self, tag: Tag) -> bool:
        """
        :param tag: Tag - tag to check
        :return:
        1. Choose only 'li'
        2. Filter if element in class from exclude_categories
        3. Exclude not root links. For example: .../catalog/detyam/shkola
        """
        exclude_categories = {'airticket', 'brands', 'promo-offer'}
        return tag.name == 'li' and \
            not set(tag['class']) & exclude_categories and \
            re.fullmatch(self.base_catalog_pattern.format('[^/?]+'), tag.find('a')['href'])

    def _parse_all_descendants(self, nodes: List[Node], level: int = 0) -> List[Node]:
        for i, node in enumerate(nodes):
            # Для отладки
            if level in [0, 1]:
                import time
                import datetime
                hour = datetime.datetime.fromtimestamp(time.time()).hour
                minute = datetime.datetime.fromtimestamp(time.time()).minute
                second = datetime.datetime.fromtimestamp(time.time()).second
                if level == 0:
                    print(f'{i + 1}/{len(nodes)} - {node.name}, time: {hour:00.0f}:{minute:00.0f}:{second:00.0f}, '
                          f'level {level}')
                elif level == 1:
                    print(f'\t{i + 1}/{len(nodes)} - {node.name}, time: {hour:00.0f}:{minute:00.0f}:{second:00.0f}, '
                          f'level {level}')
            # Прям до сюда
            descendants_bs, is_captcha, _ = self.connector.get_page(RequestBody(node.mp_url, 'get'))

            if level == 0:
                try:
                    all_items = descendants_bs.find('ul', class_='maincatalog-list-2').findAll('li')
                except AttributeError:
                    all_items = descendants_bs.find('ul', class_='maincatalog-list-1').findAll('li')

                for item in all_items:
                    url = self.config.base_url + item.find('a')['href']
                    node.descendants.append(self._get_node(item.text, url, node, level))
            else:
                try:
                    all_items = descendants_bs.find('div', class_='catalog-sidebar').findAll('li')
                except AttributeError:
                    continue

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
                        url = self.config.base_url + item.find('a')['href']
                        node.descendants.append(self._get_node(item.text, url, node, level))
            self._parse_all_descendants(node.descendants, level + 1)
        return nodes

    def _get_node(self, name: str, url: str, parent: Node, level: int) -> Node:
        new_node = Node(name, url, parent=parent)
        category_id = self._save_node_in_db(new_node, parent, level)
        new_node.db_id = category_id
        return new_node

    def _save_node_in_db(self, node: Node, parent_node: Node, level: int) -> int:
        parent = ItemCategory.objects.get(name=parent_node.name, mp_category_url=parent_node.mp_url,
                                          mp_source=self.mp_source, level=level)
        category, _ = ItemCategory.objects.get_or_create(name=node.name, mp_category_url=node.mp_url,
                                                         mp_source=self.mp_source, parent=parent)
        return category.id

    def _check_db_consistency(self) -> None:
        pass

    def _save_all_results_in_db(self, parsed_nodes: List[Node], parent: TreeQuerySet = None) -> None:
        for parsed_node in parsed_nodes:
            if parent is not None:
                category, is_created = ItemCategory.objects.get_or_create(name=parsed_node.name,
                                                                          mp_source=self.mp_source,
                                                                          parent=parent)
            else:
                # If you don't specify level, you get multiple object exception
                category, is_created = ItemCategory.objects.get_or_create(name=parsed_node.name,
                                                                          mp_source=self.mp_source,
                                                                          level=0)
            category.mp_category_url = parsed_node.mp_url
            category.save()
            parsed_node.db_id = category.id
            self._save_all_results_in_db(parsed_node.descendants, parent=category)
