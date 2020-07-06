import time
from typing import List, Dict, Tuple, Set, Union, Any, Callable
from datetime import timedelta
from collections import defaultdict

from django.db.models.base import ModelBase
from django.utils.timezone import now
from bs4 import BeautifulSoup
from bs4.element import Tag

from core.mp_scrapers.configs import WILDBERRIES_CONFIG
from core.utils.connector import Connector
from core.types import RequestBody
from core.models import Marketplace, MarketplaceScheme, ItemCategory, Item, Brand, Colour, Image, Seller


class WildberriesItemScraper:
    def __init__(self):
        self.config = WILDBERRIES_CONFIG
        self.connector = Connector(use_proxy=self.config.use_proxy)
        self.mp_source = self._get_mp_wb()
        self.xmlhttp_header = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/83.0.4103.116 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

    def update_from_mp(self) -> None:
        self._increment_item_update(start_from=1)
        self._in_category_update()
        self._individual_item_update()

    @staticmethod
    def _get_mp_wb() -> Marketplace:
        scheme_qs = MarketplaceScheme.objects.get_or_create(name='FBM')[0]
        mp_wildberries, is_created = Marketplace.objects.get_or_create(name='Wildberries')
        if is_created:
            mp_wildberries.working_schemes.add(scheme_qs)
            mp_wildberries.save()
        return mp_wildberries

    def _increment_item_update(self, start_from: int = 1) -> None:
        # max_item_id = self._get_max_item_id()
        max_item_id = 13999999
        print(f'Upper bound found: {max_item_id}')

        start = time.time()
        for i in range(start_from, max_item_id + 1, self.config.bulk_item_step):
            print(f'{i} elapsed {(time.time() - start):0.0f} seconds')
            start = time.time()

            indexes_to_request = list(range(i, min(max_item_id + 1, i + self.config.bulk_item_step)))
            items_result = self._get_item_or_seller_info(indexes_to_request, self.config.item_url, ';', )
            sellers_result = self._get_item_or_seller_info(indexes_to_request,
                                                           self.config.seller_url, ',', is_special_header=True)

            if items_result['state'] == 0 and sellers_result['resultState'] == 0:
                seller_id_to_name = {i['cod1S']: i['supplierName'] for i in sellers_result['value']}
                for item in items_result['data']['products']:
                    item['sellerName'] = seller_id_to_name.get(item['id'])
                self._add_items_to_db(items_result['data']['products'])
            elif items_result['state'] == 0:
                print(f'Error result in {i}: {sellers_result}')
                self._add_items_to_db(items_result['data']['products'])
            else:
                print(f'Error result in {i}: {items_result}')

    def _get_max_item_id(self) -> int:
        try:
            latest = Item.objects.latest('mp_id').mp_id
        except Item.DoesNotExist:
            latest = 1

        if latest == 1:
            step_size = 5000000
        else:
            step_size = 100000
        lower, upper = self._get_rough_bounds(latest, step_size)
        return self._get_max_in_bounds(lower, upper)

    def _get_rough_bounds(self, latest: int, step_size: int) -> Tuple[int, int]:
        indexes_to_request = [latest, latest + step_size]
        result = self._get_item_or_seller_info(indexes_to_request, self.config.item_url, ';')

        # Find roughly lower and upper bounds
        while result['state'] == 0:
            latest += step_size
            indexes_to_request = [latest, latest + step_size]
            result = self._get_item_or_seller_info(indexes_to_request, self.config.item_url, ';')
        return latest, latest + step_size

    def _get_max_in_bounds(self, min_id: int, max_id: int) -> int:
        middle = ((max_id - min_id) // 2) + min_id

        if middle == min_id:
            return middle
        else:
            indexes_to_request = [min_id, middle]
            result = self._get_item_or_seller_info(indexes_to_request, self.config.item_url, ';')
            if result['state'] == 0:
                return self._get_max_in_bounds(middle + 1, max_id)
            else:
                return self._get_max_in_bounds(min_id, middle - 1)

    def _get_item_or_seller_info(self, indexes: List[int], url: str, sep: str, is_special_header: bool = False) -> Dict:
        indexes = sep.join(map(str, indexes))
        url = url.format(indexes)
        headers = self.xmlhttp_header if is_special_header else None
        return self.connector.get_page(RequestBody(url, method='get', parsing_type='json', headers=headers))

    def _add_items_to_db(self, items: List[Dict]) -> List[Item]:
        brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info = self._aggregate_info_from_items(items)

        self._fill_nones_in_items(brand_id_to_idx, items_info, Brand, 'brand', 'mp_id')
        self._fill_nones_in_items(colour_id_to_idx, items_info, Colour, 'colour', 'mp_id')
        self._fill_nones_in_items(seller_id_to_idx, items_info, Seller, 'seller', 'name')

        last_parsed_time = now() - timedelta(days=1)
        new_items, old_items = [], []
        for item in items_info:
            create_params = {'name': item['name'], 'mp_id': item['mp_id'], 'mp_source': self.mp_source,
                             'root_id': item['root_id'], 'brand': item['brand'], 'colour': item['colour'],
                             'size_name': item['size_name'], 'size_orig_name': item['size_orig_name'],
                             'seller': item['sellerName']}
            get_params = {'name': item['name'], 'mp_id': item['mp_id'], 'mp_source': self.mp_source,
                          'root_id': item['root_id'], 'brand': item['brand'], 'colour': item['colour'],
                          'seller': item['sellerName']}
            try:
                old_items.append(Item.objects.get(**get_params))
                old_items[-1].last_parsed_time = last_parsed_time
            except Item.DoesNotExist:
                new_items.append(Item(**create_params))
            except Item.MultipleObjectsReturned:
                repeating_items = Item.objects.filter(**get_params)
                for repeating_item in repeating_items[1:]:
                    repeating_item.delete()
                old_items.append(repeating_items[0])
                old_items[-1].last_parsed_time = last_parsed_time

        if old_items:
            Item.objects.bulk_update(old_items, ['last_parsed_time'])

        if new_items:
            new_items = Item.objects.bulk_create(new_items)
            for item in new_items:
                item.last_parsed_time = last_parsed_time
            Item.objects.bulk_update(new_items, ['last_parsed_time'])

        return old_items + new_items

    def _aggregate_info_from_items(self, items: List[Dict]) -> Tuple[
        Dict[Union[str, int], List[int]], Dict[Union[str, int], List[int]], Dict[Union[str, int], List[int]], List[
            Dict]]:
        brand_id_to_idx, colour_id_to_idx = defaultdict(list), defaultdict(list)
        seller_id_to_idx, items_info = defaultdict(list), []
        for item in items:
            if item['colors']:
                for colour in item['colors']:
                    self._fill_objects(brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info, item, colour)
            else:
                colour = {'name': '', 'mp_id': None}
                self._fill_objects(brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info, item, colour)
        return brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info

    def _fill_objects(self, brand_id_to_idx: Dict[Union[str, int], List[int]],
                      colour_id_to_idx: Dict[Union[str, int], List[int]],
                      seller_id_to_idx: Dict[Union[str, int], List[int]], items_info: List[Dict], item: Dict,
                      colour: Union[Dict, None]) -> None:
        new_item_info = {'name': item['name'], 'mp_id': item['id'], 'root_id': item['root'], 'brand': None,
                         'colour': None, 'size_name': '', 'size_orig_name': '', 'seller': None}
        if item['sizes']:
            new_item_info['size_name'] = item['sizes'][0]['name']
            new_item_info['size_orig_name'] = item['sizes'][0]['origName']
        items_info.append(new_item_info)

        brand_params = {'name': item['brand'], 'mp_source': self.mp_source, 'mp_id': item['brandId']}
        self._prepare_model(items_info, brand_id_to_idx, Brand, brand_params, 'brand', 'mp_id')

        seller_params = {'name': item['sellerName'], 'mp_source_id': self.mp_source.id}
        self._prepare_model(items_info, seller_id_to_idx, Seller, seller_params, 'seller', ['name', 'mp_source_id'])

        colour_params = {'name': colour['name'], 'mp_source': self.mp_source, 'mp_id': colour['id']}
        self._prepare_model(items_info, colour_id_to_idx, Colour, colour_params, 'colour', 'mp_id')

    @staticmethod
    def _prepare_model(to_fill: List[Dict], fill_id_to_idx: Dict[Union[str, int], List[int]],
                       model: Union[Brand, Colour, Seller, Callable], params: Dict[str, Any], model_name: str,
                       field_for_ident: Union[str, List[str]]) -> None:
        try:
            to_fill[-1][model_name] = model.objects.get(**params)
        except model.DoesNotExist:
            to_fill[-1][model_name] = model(**params)
            if isinstance(field_for_ident, str):
                fill_id_to_idx[params[field_for_ident]].append(len(to_fill) - 1)
            else:
                field_name = ' '.join([str(params[name]) for name in field_for_ident])
                fill_id_to_idx[field_name].append(len(to_fill) - 1)
        except model.MultipleObjectsReturned:
            repeating_items = model.objects.filter(**params)
            to_fill[-1][model_name] = repeating_items[0]
            for repeating_item in repeating_items[1:]:
                repeating_item.delete()

    @staticmethod
    def _fill_nones_in_items(id_to_idx: Dict[Union[str, int], List[int]],
                             items_info: List[Dict], model: Union[ModelBase, Brand, Colour, Seller], model_name: str,
                             field_to_ident: Union[str, List[str]]) -> None:
        new_models = [items_info[idxs[0]][model_name] for idxs in id_to_idx.values()]
        new_models = model.objects.bulk_create(new_models)
        for model in new_models:
            if isinstance(field_to_ident, str):
                idxs = id_to_idx[model.__getattribute__(field_to_ident)]
            else:
                key = ' '.join([model.__getattribute__(field) for field in field_to_ident])
                idxs = id_to_idx[key]
            for i in idxs:
                items_info[i][model_name] = model

    def _in_category_update(self) -> None:
        category_leaves = ItemCategory.objects.filter(children__isnull=True)

        for category_leaf in category_leaves:
            self._process_all_pages(category_leaf)

    def _process_all_pages(self, category_leaf: ItemCategory):
        counter = 1
        while True:
            page_num = f'?page={counter}'
            bs, _, status_code = self.connector.get_page(RequestBody(category_leaf.mp_category_url + page_num,
                                                                     'get'))
            if status_code == 404:
                break
            else:
                self._process_items_on_page(bs, category_leaf)
            counter += 1

    def _process_items_on_page(self, bs: BeautifulSoup, category_leaf: ItemCategory):
        all_items = bs.find('div', class_='catalog_main_table').findAll('div', class_='dtList')
        item_ids, item_imgs = self._extract_ids_imgs_from_page(all_items)

        # Bulk create images
        img_objects = [Image(mp_link=img, mp_source=self.mp_source) for img in item_imgs]
        Image.objects.bulk_create(img_objects, ignore_conflicts=True)

        available_items = Item.objects.filter(mp_id__in=item_ids)
        available_ids = self._add_category_and_imgs(available_items, category_leaf, item_imgs)
        not_in_db_ids = set(item_ids) - available_ids

        item_json = self._get_indexes_info(list(not_in_db_ids))
        new_items = self._add_items_to_db(item_json['data']['products'])
        self._add_category_and_imgs(new_items, category_leaf, item_imgs)

    @staticmethod
    def _add_category_and_imgs(items: List[Item], category_leaf: ItemCategory,
                               item_imgs: Dict[int, str]) -> Set[int]:
        updated_ids = set()
        for item in items:
            item.categories.add(category_leaf)
            item.images.add(item_imgs[item.mp_id])
            updated_ids.add(item.id)
        return updated_ids

    @staticmethod
    def _extract_ids_imgs_from_page(all_items: List[Tag]) -> Tuple[List[int], Dict[int, str]]:
        mp_ids, imgs = [], {}
        for item in all_items:
            mp_ids.append(int(item['data-popup-nm-id']))
            imgs[int(item['data-popup-nm-id'])] = 'https:' + item.find('img')['src']
        return mp_ids, imgs

    def _individual_item_update(self):
        items = self._get_items_no_categories()
        for item in items:
            item_bs, is_captcha, status_code = self.connector.get_page(RequestBody('url', 'get'))
            category = self._parse_category(item_bs)
            item.categories.add(category)

    def _get_items_no_categories(self) -> List[Item]:
        Item.objects.filter(categories__isnull=True)

    def _parse_category(self, item_bs: BeautifulSoup) -> ItemCategory:
        pass

    def _sellers_update(self):
        pass
