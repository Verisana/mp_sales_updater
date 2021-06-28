import asyncio
import pickle
import re
from typing import List

from bs4 import BeautifulSoup
from bs4.element import Tag
from django.utils.timezone import now
from mptt.querysets import TreeQuerySet

from core.exceptions import SalesUpdaterError
from core.models import ItemCategory
from core.mp_scrapers.wildberries.wildberries_base import WildberriesBaseScraper, save_object_for_logging
from core.types import RequestBody
from core.utils.trees import Node
from core.utils.logging_helpers import get_logger

logger = get_logger()


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

    def update_from_mp(self, start_from: int = None) -> int:
        logger.info(f'Started parsing categories from marketplace')
        bs, is_captcha, _ = asyncio.run(self.connector.get_page(RequestBody(self.config.base_categories_url, 'get',
                                                                            headers=self.all_categories_headers)))
        try:
            parsed_nodes = self._parse_bs_response(bs)
        except KeyboardInterrupt:
            return -1

        with open(f"{now().astimezone().strftime('%Y%m%d')}_parsed_nodes.p", 'wb') as f:
            pickle.dump(parsed_nodes, f)

        self._check_db_consistency()
        return 0

    def update_from_file(self, load_file: str) -> int:
        logger.info(f'Started parsing categories from file')
        parsed_nodes = pickle.load(open(load_file, 'rb'))
        try:
            self._save_all_results_in_db(parsed_nodes)
        except KeyboardInterrupt:
            return -1

        self._check_db_consistency()
        return 0

    def _parse_bs_response(self, bs: BeautifulSoup) -> List[Node]:
        root_node_tags = bs.find('ul', class_='topmenus').find_all(self._check_root_matching)

        root_nodes = []
        for tag in root_node_tags:
            name, url = tag.text, tag.find('a')['href']
            new_node = Node(name, url, parent=None)

            category, _ = ItemCategory.objects.get_or_create(
                name=new_node.name, marketplace_category_url=new_node.marketplace_url,
                marketplace_source=self.marketplace_source, parent=None)
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
        4. Exclude if category name in exclude_categories
        """
        exclude_categories = {'airticket', 'brands', 'promo-offer', 'тренды'}
        return tag.name == 'li' and \
            not set(tag['class']) & exclude_categories and \
            re.fullmatch(self.base_catalog_pattern.format('.+'), tag.find('a')['href']) and \
            tag.find('a').text.lower() not in exclude_categories

    def _parse_all_descendants(self, nodes: List[Node], level: int = 0) -> List[Node]:
        for i, node in enumerate(nodes):
            # For DEBUGGING
            if level in [0, 1, 2]:
                message = f'{i + 1}/{len(nodes)} - {node.name}, level {level}'
                if level == 0:
                    logger.debug(message)
                elif level == 1:
                    logger.debug('\t'+message)
                elif level == 2:
                    logger.debug('\t\t'+message)
            # Прям до сюда

            descendants_bs, is_captcha, _ = asyncio.run(self.connector.get_page(
                RequestBody(node.marketplace_url, 'get')))

            # Update number of items in category
            items_number = self._get_items_number(descendants_bs)
            current_category = ItemCategory.objects.get(id=node.db_id)
            current_category.marketplace_items_in_category = items_number
            current_category.save()

            if level == 0:
                all_items = self._extract_catalogs_from_root(descendants_bs)
                for item in all_items:
                    url = self.config.base_url + item.find('a')['href']
                    item_name = item.find('a').text.strip('\n') if item.find('a').text.strip('\n') else item.find(
                        'a')['title']
                    node.descendants.append(self._get_node(item_name, url, node))
            else:
                try:
                    all_items = descendants_bs.find('div', class_='catalog-sidebar').find_all('li')
                except AttributeError:
                    logger.warning("Can't find catalog sidebar")
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
                        node.descendants.append(self._get_node(item.text, url, node))
            self._parse_all_descendants(node.descendants, level + 1)
        return nodes

    @staticmethod
    def _get_items_number(bs: BeautifulSoup) -> int:
        num_tag = bs.find_all('span', class_='goods-count')
        if len(num_tag) == 1:
            # Just parsing number in tag
            return int(num_tag[0].text.strip('\n').strip(' ').split(' ')[0])
        else:
            return 0

    @staticmethod
    def _extract_catalogs_from_root(descendants_bs: BeautifulSoup) -> List[Tag]:
        all_items = descendants_bs.find('ul', class_='maincatalog-list-2')
        if all_items is not None:
            return all_items.findAll('li', recursive=False)

        category_banners = descendants_bs.findAll('div', class_='banners-zones')
        # Looking for banners "catalog" in URL and certain class in tag to exclude irrelevant items
        all_items = list(filter(
            lambda tag: 'j-banner-shown-stat' in tag.find('a')['class'] and 'catalog' in tag.find('a')['href'],
            category_banners))
        if len(all_items) > 0:
            return all_items

        logger.error('Something is wrong while getting catalog from root in _extract_catalogs_from_root '
                     'Corresponding descendants_bs is saved')
        save_object_for_logging(descendants_bs.prettify(), 'descendants_bs_root.html', type='string')
        raise SalesUpdaterError

    def _get_node(self, name: str, url: str, parent: Node) -> Node:
        new_node = Node(name, url, parent=parent)
        category_id = self._save_node_in_db(new_node, parent)
        new_node.db_id = category_id
        return new_node

    def _save_node_in_db(self, node: Node, parent_node: Node) -> int:
        parent = ItemCategory.objects.get(id=parent_node.db_id)
        category, _ = ItemCategory.objects.get_or_create(name=node.name, marketplace_category_url=node.marketplace_url,
                                                         marketplace_source=self.marketplace_source, parent=parent)
        return category.id

    def _check_db_consistency(self) -> None:
        pass

    def _save_all_results_in_db(self, parsed_nodes: List[Node], parent: TreeQuerySet = None) -> None:
        for i, parsed_node in enumerate(parsed_nodes):
            if parent is None:
                logger.info(f'{i + 1}/{len(parsed_nodes)}. Saving {parsed_node.name}')

            category, is_created = ItemCategory.objects.get_or_create(name=parsed_node.name,
                                                                      marketplace_source=self.marketplace_source,
                                                                      parent=parent)
            if category.marketplace_items_in_category != parsed_node.items_number:
                category.marketplace_items_in_category = parsed_node.items_number
            try:
                category.marketplace_category_url = parsed_node.marketplace_url
            except AttributeError:
                category.marketplace_category_url = parsed_node.mp_url
            category.save()
            parsed_node.db_id = category.id
            self._save_all_results_in_db(parsed_node.descendants, parent=category)
