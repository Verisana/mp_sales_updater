import asyncio
import multiprocessing
import time
from collections import defaultdict
from typing import List, Dict, Tuple, Set, Union, Any, Callable

from bs4 import BeautifulSoup
from bs4.element import Tag
from django.db import connection, transaction
from django.db.utils import DataError
from django.db.models import Q
from django.db.models.base import ModelBase
from django.utils.timezone import now

from core.exceptions import SalesUpdaterError
from core.models import ItemCategory, Item, Brand, Colour, Image, Seller, ItemPosition
from core.mp_scrapers.wildberries.wildberries_base import WildberriesBaseScraper, save_object_for_logging
from core.mp_scrapers.wildberries.wildberries_revisions import WildberriesRevisionScraper
from core.types import RequestBody
from core.utils.logging_helpers import get_logger

logger = get_logger()


class WildberriesItemBase(WildberriesBaseScraper):
    xmlhttp_header: Dict[str, str]

    def __init__(self):
        self.xmlhttp_header = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/83.0.4103.116 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        self.lock = multiprocessing.Manager().Lock()

    def update_from_mp(self, start_from: int = None) -> int:
        raise NotImplementedError

    async def get_api_info(self, indices: List[int], type_info: str = 'items') -> Dict:
        counter = 0
        if type_info == 'items':
            indices_joined = ';'.join(map(str, indices))
            url = self.config.items_api_url.format(indices_joined)
            headers = None
        elif type_info == 'sellers':
            indices_joined = ','.join(map(str, indices))
            url = self.config.seller_url.format(indices_joined)
            headers = self.xmlhttp_header
        else:
            logger.error(f'Type info {type_info} can not be recognized. Check function calls')
            raise SalesUpdaterError
        while True:
            counter += 1
            json_result, _, _ = await self.connector.get_page(RequestBody(url, method='get',
                                                                          parsing_type='json', headers=headers))
            if self._is_valid_result(json_result):
                return json_result
            elif counter > 10:
                save_object_for_logging(url, f'requested_URL.p')
                save_object_for_logging(json_result, f'returned_json.p')
                logger.warning(f"Could not get json api for all requested items "
                               f"for indices count {len(indices)}")
                return json_result

    def add_items_to_db(self, items: List[Dict]) -> List[Item]:
        self.lock.acquire()
        brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info = self._aggregate_info_from_items(items)

        self._fill_nones_in_items(brand_id_to_idx, items_info, Brand, 'brand', 'marketplace_id')
        self._fill_nones_in_items(colour_id_to_idx, items_info, Colour, 'colour', 'marketplace_id')
        self._fill_nones_in_items(seller_id_to_idx, items_info, Seller, 'seller', 'name')
        self.lock.release()

        current_time = now()
        new_items, old_items, colours_old_items, colours_new_items = [], [], [], []
        fields_to_update = ['name', 'size_name', 'size_orig_name']

        last_marketplace_id = 0
        self.lock.acquire()
        for i, item in enumerate(items_info):
            create_params = {'name': item['name'], 'marketplace_id': item['marketplace_id'],
                             'marketplace_source': self.marketplace_source, 'root_id': item['root_id'],
                             'brand': item['brand'], 'size_name': item['size_name'],
                             'size_orig_name': item['size_orig_name'], 'seller': item['seller'],
                             'revisions_next_parse_time': current_time, 'is_digital': item['is_digital'],
                             'is_adult': item['is_adult']}
            get_params = {'marketplace_id': item['marketplace_id'], 'marketplace_source': self.marketplace_source}
            if i > 0:
                last_marketplace_id = items_info[i - 1]['marketplace_id']
            try:
                existing_item = Item.objects.get(**get_params)
            except Item.DoesNotExist:
                new_item = Item(**create_params)
                self._add_item_and_fill_colours(new_items, colours_new_items, last_marketplace_id, new_item,
                                                item['colour'].pk)
                continue
            except Item.MultipleObjectsReturned:
                logger.error(f'Something is wrong. You should get one object for params: {get_params}')
                existing_items = Item.objects.filter(**get_params)
                existing_item = existing_items[0]
                for duplicate_item in existing_items[1:]:
                    duplicate_item.delete()

            self._update_existing_item(existing_item, item, fields_to_update)
            self._add_item_and_fill_colours(old_items, colours_old_items,
                                            last_marketplace_id, existing_item, item['colour'].pk)
        if old_items:
            with transaction.atomic():
                Item.objects.bulk_update(old_items, fields_to_update)
                for old_item, colour_pks in zip(old_items, colours_old_items):
                    old_item.colours.add(*colour_pks)

        if new_items:
            with transaction.atomic():
                try:
                    new_items = Item.objects.bulk_create(new_items)
                except DataError as e:
                    save_object_for_logging(new_items, 'corrupted_new_items.p')
                    logger.exception(e)
                    raise e
                for new_item, colour_pks in zip(new_items, colours_new_items):
                    new_item.colours.add(*colour_pks)

        self.lock.release()

        all_items = old_items + new_items
        if len(all_items) > 0:
            all_items.sort(key=lambda x: x.marketplace_id)
        return all_items

    def add_empty_items_to_db(self, items: List[Dict]) -> List[Item]:
        current_time = now()
        new_items, old_items = [], []

        self.lock.acquire()
        for i, item in enumerate(items):
            create_params = {'name': item['name'], 'marketplace_id': item['marketplace_id'],
                             'marketplace_source': self.marketplace_source, 'revisions_next_parse_time': current_time}

            get_params = {'marketplace_id': item['marketplace_id'], 'marketplace_source': self.marketplace_source}
            try:
                old_items.append(Item.objects.get(**get_params))
            except Item.DoesNotExist:
                new_items.append(Item(**create_params))
                continue
            except Item.MultipleObjectsReturned:
                logger.error(f'Something is wrong. You should get one object for params: {get_params}')
                existing_items = Item.objects.filter(**get_params)
                old_items.append(existing_items[0])
                for duplicate_item in existing_items[1:]:
                    duplicate_item.delete()

        if new_items:
            new_items = Item.objects.bulk_create(new_items)
        self.lock.release()

        all_items = old_items + new_items
        if len(all_items) > 0:
            all_items.sort(key=lambda x: x.marketplace_id)
        return all_items

    @staticmethod
    def _is_valid_result(json_result: Dict) -> bool:
        # We only want to check for seller updates
        if 'state' in json_result.keys():
            return True
        else:
            if json_result['resultState'] == 0:
                try:
                    _ = {i['cod1S']: i['supplierName'] for i in json_result['value']}
                except KeyError as e:
                    logger.warning(f'KeyError caught json_result: {e}')
                    return False
            return True

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
                colour = {'name': ''}
                self._fill_objects(brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info, item, colour)
        return brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info

    def _fill_objects(self, brand_id_to_idx: Dict[Union[str, int], List[int]],
                      colour_id_to_idx: Dict[Union[str, int], List[int]],
                      seller_id_to_idx: Dict[Union[str, int], List[int]], items_info: List[Dict], item: Dict,
                      colour: Dict) -> None:
        new_item_info = {'name': item['name'][:255], 'marketplace_id': item['id'], 'root_id': item['root'],
                         'brand': None, 'colour': None, 'size_name': '', 'size_orig_name': '', 'seller': None,
                         'is_digital': item['isDigital'], 'is_adult': item['isAdult']}
        if item['sizes']:
            new_item_info['size_name'] = item['sizes'][0]['name']
            new_item_info['size_orig_name'] = item['sizes'][0]['origName']
        items_info.append(new_item_info)

        brand_name = item.get('brand') if item.get('brand') is not None else ''
        brand_params = {'name': brand_name, 'marketplace_source': self.marketplace_source,
                        'marketplace_id': item.get('brandId')}
        self._prepare_model(items_info, brand_id_to_idx, Brand, brand_params, 'brand', 'marketplace_id')

        seller_name = item.get('sellerName') if item.get('sellerName') is not None else ''
        seller_params = {'name': seller_name, 'marketplace_source_id': self.marketplace_source.id}
        self._prepare_model(items_info, seller_id_to_idx, Seller, seller_params, 'seller',
                            ['name', 'marketplace_source_id'])

        colour_name = colour.get('name') if colour.get('name') is not None else ''
        colour_params = {'name': colour_name, 'marketplace_source': self.marketplace_source,
                         'marketplace_id': colour.get('id')}
        self._prepare_model(items_info, colour_id_to_idx, Colour, colour_params, 'colour', 'marketplace_id')

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
                idxs: List[int] = id_to_idx[model.__getattribute__(field_to_ident)]
            else:
                key = ' '.join([model.__getattribute__(field) for field in field_to_ident])
                idxs = id_to_idx[key]
            for i in idxs:
                items_info[i][model_name] = model

    @staticmethod
    def _update_existing_item(item: Item, item_info: Dict, fields_to_update: List[str]) -> None:
        for field in fields_to_update:
            item.__setattr__(field, item_info.get(field))

    @staticmethod
    def _add_item_and_fill_colours(items: List[Item], colours: List[List[int]],
                                   last_mp_id: int, item: Item, colour_pk: int):
        if last_mp_id != item.marketplace_id:
            items.append(item)
            colours.append([colour_pk])
        else:
            colours[-1].append(colour_pk)


class WildberriesItemScraper(WildberriesItemBase):
    def __init__(self):
        super().__init__()
        logger.debug(f'Start check parse times')
        self._check_parse_times()
        logger.debug(f'Stop check parse times')
        self.revision_scraper = WildberriesRevisionScraper()

    @staticmethod
    def _check_parse_times():
        categories = ItemCategory.objects.filter(Q(start_parse_time__isnull=False) | Q(next_parse_time__isnull=True))
        current_time = now()
        for category in categories:
            category.start_parse_time = None
            category.next_parse_time = current_time
        ItemCategory.objects.bulk_update(categories, ['start_parse_time', 'next_parse_time'])

    def update_from_mp(self, start_from: int = None) -> int:
        start = time.time()
        connection.close()
        category = self._get_category()
        if category is None:
            return -1
        logger.info(f'Start update from mp for {category}')
        self._process_all_pages(category)
        logger.debug(f'{category} elapsed {(time.time() - start):0.0f} seconds')
        return 0

    def _get_category(self) -> ItemCategory:
        with transaction.atomic():
            start = time.time()
            num_items = ItemCategory.objects.filter(
                marketplace_source=self.marketplace_source, is_deleted=False,
                start_parse_time__isnull=True, next_parse_time__lte=now()).count()
            logger.info(f'Remained {num_items} operation elapsed {time.time() - start:0.2f}')

            category = ItemCategory.objects.select_for_update(skip_locked=True).exclude(children__isnull=False).filter(
                marketplace_source=self.marketplace_source, is_deleted=False,
                start_parse_time__isnull=True, next_parse_time__lte=now()).first()
            if category is not None:
                category.start_parse_time = now()
                category.save()
                return category

    def _process_all_pages(self, category: ItemCategory, counter: int = 1, debug: bool = False):
        while True:
            start = time.time()
            page_num = f'?page={counter}'
            bs, _, status_code = asyncio.run(self.connector.get_page(RequestBody(
                category.marketplace_category_url + page_num, 'get')))
            if status_code not in [200, 404]:
                logger.warning(f'Bad response for {category} from marketplace. Try one more time')
                continue
            is_no_items = self._is_items_not_found(bs, category, status_code)
            if status_code == 404 or is_no_items:
                category.next_parse_time = now() + self.config.items_parse_frequency
                category.start_parse_time = None
                if is_no_items:
                    category.marketplace_items_in_category = 0
                category.save()
                break
            else:
                self._update_num_items_in_category(bs, category)
                self._process_items_on_page(bs, category, counter - 1)
            logger.info(f'\tPage number {counter} for {category} done in {time.time() - start:0.2f} sec.')
            counter += 1
            if debug:
                break

    @staticmethod
    def _is_items_not_found(bs: BeautifulSoup, category: ItemCategory, status_code: int) -> bool:
        if status_code == 404:
            return False

        all_items = bs.find('div', class_='catalog_main_table')
        if all_items is None:
            all_items = bs.find('div', id='divGoodsNotFound')
            if all_items is not None:
                logger.info(f'Empty category {category}')
            else:
                save_object_for_logging(bs, f'bs_{category}.txt')
                logger.error(f'Something is wrong while getting divGoodsNotFound for {category}. '
                             f'Beautiful Soup response has been saved')
                raise SalesUpdaterError
            return True
        else:
            return False

    @staticmethod
    def _update_num_items_in_category(bs: BeautifulSoup, category: ItemCategory):
        num_tag = bs.findAll('span', class_='goods-count')
        if len(num_tag) == 1:
            # Just parsing number in tag
            num_tag = int(num_tag[0].text.strip('\n').strip(' ').split(' ')[0])
            category.marketplace_items_in_category = num_tag
            category.save()
        else:
            logger.error(f'Something is wrong while getting goods count {num_tag}')

    def _process_items_on_page(self, bs: BeautifulSoup, category: ItemCategory, page_num: int):
        all_items = bs.find('div', class_='catalog_main_table').findAll('div', class_='dtList')
        item_ids, img_id_to_objs, img_link_to_ids = self._extract_info_from_page(all_items)

        self._create_or_update_imgs(img_link_to_ids, img_id_to_objs)

        full_items_info = asyncio.run(self._get_full_api_info(item_ids))

        empty_ids = list(set(item_ids) - set([item['id'] for item in full_items_info]))
        if empty_ids:
            empty_items_info = self._get_empty_items(empty_ids, category)
            empty_items = self.add_empty_items_to_db(empty_items_info)
            self._add_category_and_imgs(empty_items, category, img_id_to_objs)

        full_items = self.add_items_to_db(full_items_info)
        self._add_category_and_imgs(full_items, category, img_id_to_objs)

        self.revision_scraper.update_from_args(full_items, full_items_info)
        self._create_positions(item_ids, category, page_num)

    def _extract_info_from_page(self, all_items: List[Tag]) -> Tuple[List[int], Dict[int, Image], Dict[str, int]]:
        marketplace_ids, imgs, link_to_ids = [], {}, {}
        for item in all_items:
            found_image = False
            for tag in item.findAll('img'):
                link = tag.get('src')
                if link is not None and 'blank' not in link:
                    img_link = 'https:' + link
                    img_obj = Image(marketplace_link=img_link, marketplace_source=self.marketplace_source,
                                    next_parse_time=now())
                    imgs[int(item['data-popup-nm-id'])] = img_obj
                    link_to_ids[img_link] = int(item['data-popup-nm-id'])
                    marketplace_ids.append(int(item['data-popup-nm-id']))
                    found_image = True
                    break
            if not found_image:
                logger.error(f'Found item with no image. Check it:\n\n{item.prettify()}')
                marketplace_ids.append(int(item['data-popup-nm-id']))
        return marketplace_ids, imgs, link_to_ids

    def _create_or_update_imgs(self, img_link_to_ids: Dict[str, int], img_id_to_objs: Dict[int, Image]):
        self.lock.acquire()
        imgs_filtered = Image.objects.filter(marketplace_link__in=img_link_to_ids.keys())
        for img_filtered in imgs_filtered:
            item_id = img_link_to_ids[img_filtered.marketplace_link]
            img_id_to_objs[item_id] = img_filtered

        new_imgs = Image.objects.bulk_create([img for img in img_id_to_objs.values() if img.pk is None])
        self.lock.release()

        for new_img in new_imgs:
            item_id = img_link_to_ids[new_img.marketplace_link]
            img_id_to_objs[item_id] = new_img

    async def _get_full_api_info(self, item_ids: List[int]) -> List[Dict]:
        items_coroutine = self.get_api_info(item_ids, type_info='items')
        sellers_coroutine = self.get_api_info(item_ids, type_info='sellers')

        items_result, sellers_result = await asyncio.gather(items_coroutine, sellers_coroutine)

        result = []
        if items_result['state'] == 0 and sellers_result['resultState'] == 0 and items_result['data']['products']:
            seller_id_to_name = {i['cod1S']: i.get('supplierName') for i in sellers_result['value'] if
                                 i.get('supplierName') is not None}
            for item in items_result['data']['products']:
                item['sellerName'] = seller_id_to_name.get(item['id'])
            result = items_result['data']['products']
        elif items_result['state'] == 0 and items_result['data']['products']:
            logger.warning(f'Error result in {item_ids}: {sellers_result}')
            result = items_result['data']['products']
        elif items_result['state'] == 0 and not items_result['data']['products']:
            logger.info(f'Items response is empty: {items_result}')
        else:
            logger.warning(f'Error result in {item_ids}: {items_result}')

        if len(result) > 0:
            result.sort(key=lambda x: x['id'])
        return result

    def _get_empty_items(self, empty_ids: List[int], category: ItemCategory) -> List[Dict]:
        return [{'name': category.name, 'marketplace_id': mp_id,
                 'marketplace_source': self.marketplace_source} for mp_id in empty_ids]

    @staticmethod
    def _add_category_and_imgs(items: List[Item], category_leaf: ItemCategory,
                               item_imgs: Dict[int, Image]) -> Set[int]:
        updated_ids = set()
        for item in items:
            item.categories.add(category_leaf)

            image = item_imgs.get(item.marketplace_id)
            if image is not None:
                item.images.add(image)
            updated_ids.add(item.marketplace_id)
        return updated_ids

    def _create_positions(self, mp_ids: List[int], category: ItemCategory, page_num: int):
        items = Item.objects.filter(marketplace_id__in=mp_ids)
        assert len(items) == len(mp_ids)
        new_positions = []
        for i, mp_id in enumerate(mp_ids):
            position = page_num * self.config.items_per_page + (i + 1)
            item = next(filter(lambda x: x.marketplace_id == mp_id, items))
            new_positions.append(ItemPosition(item=item, category=category, position_num=position))
        ItemPosition.objects.bulk_create(new_positions)
