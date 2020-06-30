import re
import pickle
from typing import List, Dict
from itertools import product
from datetime import timedelta

from bs4 import BeautifulSoup
from bs4.element import Tag
from mptt.querysets import TreeQuerySet
from django.utils.timezone import now

from .configs import WILDBERRIES_CONFIG
from core.utils.proxy_manager import ProxyManager
from core.utils.connector import Connector
from core.types import RequestBody
from core.utils.trees import Node
from core.models import Marketplace, MarketplaceScheme, ItemCategory, Item, Brand, \
                        Colour, Size, ItemRevision, ItemImage


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
            if level in [0, 1]:
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
            # Прям до сюда
            descendants_bs, is_captcha = self.connector.get_page(RequestBody(node.mp_url, 'get'))

            if level == 0:
                try:
                    all_items = descendants_bs.find('ul', class_='maincatalog-list-2').findAll('li')
                except AttributeError:
                    all_items = descendants_bs.find('ul', class_='maincatalog-list-1').findAll('li')

                for item in all_items:
                    node.descendants.append(Node(item.text, self.config.base_url + item.find('a')['href']))
            else:
                try:
                    all_items = descendants_bs.find('div', class_='catalog-sidebar').findAll('li')
                except AttributeError as e:
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

        #import pickle
        #root_nodes = pickle.load(open('root_node_16_filled_last.p', 'rb'))

        return self._parse_all_descendants(root_nodes)

    def _check_db_consistency(self) -> bool:
        return True

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
            category.mp_category_url = parsed_node.mp_url
            category.save()
            parsed_node.db_id = category.id
            self._save_results_in_db(parsed_node.descendants, parent=category)
        return True

    def update_categories(self) -> bool:
        bs, is_captcha = self.connector.get_page(RequestBody(self.config.base_categories_url, 'get',
                                                             headers=self.all_categories_headers))

        # parsed_nodes = self._parse_bs_response(bs)
        # with open('parsed_nodes.p', 'wb') as f:
        #     pickle.dump(parsed_nodes, f)
        parsed_nodes = pickle.load(open('parsed_nodes.p', 'rb'))
        if not self._save_results_in_db(parsed_nodes):
            return False
        return self._check_db_consistency()


class WildberriesItemScraper:
    def __init__(self):
        self.config = WILDBERRIES_CONFIG
        self.connector = Connector(use_proxy=self.config.use_proxy)
        self.mp_source_id = self._get_mp_wb_id()

    def _get_mp_wb_id(self) -> int:
        scheme_qs = MarketplaceScheme.objects.get_or_create(name='FBM')[0]
        mp_wildberries, is_created = Marketplace.objects.get_or_create(name='Wildberries')
        if is_created:
            mp_wildberries.working_schemes.add(scheme_qs)
            mp_wildberries.save()
        return mp_wildberries.id

    def _get_category_leaves(self) -> List[ItemCategory]:
        pass

    def _in_category_update(self) -> bool:
        category_leaves = self._get_category_leaves()

        for category_leave in category_leaves:
            request_info = None

        return True

    def _get_max_item_id(self) -> int:
        pass

    def _create_item(self, item: Dict, brand: Brand, colour: Dict = None, size: Dict = None) -> None:
        last_parsed_time = now() - timedelta(days=1)
        new_item, _ = Item.objects.get_or_create(name=item['name'], mp_id=item['id'], root_id=item['root'],
                                                 mp_source=self.mp_source_id, brand=brand, colour=colour,
                                                 size=size, last_parsed_time=last_parsed_time)

    def _add_items_to_db(self, item: Dict) -> None:
        brand, _ = Brand.objects.get_or_create(name=item['brand'], mp_source=self.mp_source_id, mp_id=item['brandId'])

        if len(item['colors']) > 0 and len(item['sizes']) > 0:
            for colour, size in product(item['colors'], item['sizes']):
                colour, _ = Colour.objects.get_or_create(name=colour['name'], mp_source=self.mp_source_id,
                                                         mp_id=colour['id'])
                size, _ = Size.objects.get_or_create(name=size['name'], orig_name=size['origName'],
                                                     mp_source=self.mp_source_id, mp_id=size['optionId'])
                self._create_item(item, brand, colour, size)
        elif len(item['colors']) > 0 and len(item['sizes']) == 0:
            for colour in item['colors']:
                self._create_item(item, brand, colour=colour, size=None)
        elif len(item['colors']) == 0 and len(item['sizes']) > 0:
            for size in item['sizes']:
                self._create_item(item, brand, colour=None, size=size)
        elif len(item['colors']) == 0 and len(item['sizes']) == 0:
            self._create_item(item, brand, colour=None, size=None)

    def _increment_item_update(self) -> bool:
        max_item_id = self._get_max_item_id()

        for i in range(1, max_item_id+1, self.config.bulk_item_step):
            indexes_to_request = list(range(i, min(max_item_id+1, i+self.config.bulk_item_step)))
            indexes_to_request = ';'.join(indexes_to_request)

            url = self.config.item_url.format(indexes_to_request)
            result = self.connector.get_page(RequestBody(url, method='get', parsing_type='json'))

            if result['state'] == 0:
                for product in result['data']['products']:
                    self._add_items_to_db(product)
            else:
                print(f'Error result in {i}: {result}')

        return True

    def update_items(self) -> bool:
        if not self._increment_item_update():
            return False
        return self._in_category_update()


class WildberriesRevisionScraper:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.config = WILDBERRIES_CONFIG

    def get_requests(self):
        pass

    def update_items(self, responses: List[BeautifulSoup]):
        pass
