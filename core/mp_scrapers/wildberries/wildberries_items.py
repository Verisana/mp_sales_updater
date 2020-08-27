import multiprocessing
import time
from collections import defaultdict
from typing import List, Dict, Tuple, Set, Union, Any, Callable

from bs4 import BeautifulSoup
from bs4.element import Tag
from django.db import connection, transaction
from django.db.models import Max, Q
from django.db.models.base import ModelBase
from django.utils.timezone import now

from core.models import ItemCategory, Item, Brand, Colour, Image, Seller
from core.mp_scrapers.wildberries.wildberries_base import WildberriesBaseScraper, WildberriesProcessPool
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

    def update_from_mp(self, start_from: int = None) -> int:
        raise NotImplementedError

    def get_item_or_seller_info(self, indices: List[int], url: str, sep: str, is_special_header: bool = False) -> Dict:
        counter = 0
        indices_joined = sep.join(map(str, indices))
        url = url.format(indices_joined)
        headers = self.xmlhttp_header if is_special_header else None
        while True:
            counter += 1
            json_result, _, _ = self.connector.get_page(RequestBody(url,
                                                        method='get', parsing_type='json', headers=headers))
            if self._is_valid_result(json_result):
                return json_result
            elif counter > 5:
                logger.warning(f"Could not get SuppliersName for all requested items "
                               f"from {indices[0]} to {indices[-1]}")
                return json_result

    def add_items_to_db(self, items: List[Dict]) -> List[Item]:
        brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info = self._aggregate_info_from_items(items)

        self._fill_nones_in_items(brand_id_to_idx, items_info, Brand, 'brand', 'marketplace_id')
        self._fill_nones_in_items(colour_id_to_idx, items_info, Colour, 'colour', 'marketplace_id')
        self._fill_nones_in_items(seller_id_to_idx, items_info, Seller, 'seller', 'name')

        current_time = now()
        new_items, old_items, colours = [], [], []
        for item in items_info:
            create_params = {'name': item['name'], 'marketplace_id': item['marketplace_id'],
                             'marketplace_source': self.marketplace_source, 'root_id': item['root_id'],
                             'brand': item['brand'], 'size_name': item['size_name'],
                             'size_orig_name': item['size_orig_name'], 'seller': item['seller'],
                             'revisions_next_parse_time': current_time, 'is_digital': item['is_digital'],
                             'is_adult': item['is_adult']}
            get_params = {'marketplace_id': item['marketplace_id'], 'marketplace_source': self.marketplace_source}

            try:
                existing_item = Item.objects.get(**get_params)
                old_items.append(existing_item)
            except Item.DoesNotExist:
                new_item = Item(**create_params)
                try:
                    last_marketplace_id = new_items[-1].marketplace_id
                except IndexError:
                    last_marketplace_id = None
                if last_marketplace_id != new_item.marketplace_id:
                    new_items.append(new_item)
                    colours.append([item['colour'].pk])
                else:
                    colours[-1].append(item['colour'].pk)
            except Item.MultipleObjectsReturned:
                logger.error(f'Something is wrong. You should get one object for params: {get_params}')
                continue

        if new_items:
            with transaction.atomic():
                new_items = Item.objects.bulk_create(new_items)
                for new_item, colour_pks in zip(new_items, colours):
                    new_item.colours.add(*colour_pks)

        return old_items + new_items

    @staticmethod
    def _is_valid_result(json_result: Dict) -> bool:
        # We only want to check for seller updates
        if 'state' in json_result.keys():
            return True
        else:
            try:
                if json_result['resultState'] == 0:
                    _ = {i['cod1S']: i['supplierName'] for i in json_result['value']}
                return True
            except KeyError as e:
                logger.warning(f'KeyError caught json_result: {e}')
                return False

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
        new_item_info = {'name': item['name'], 'marketplace_id': item['id'], 'root_id': item['root'], 'brand': None,
                         'colour': None, 'size_name': '', 'size_orig_name': '', 'seller': None,
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
                idxs = id_to_idx[model.__getattribute__(field_to_ident)]
            else:
                key = ' '.join([model.__getattribute__(field) for field in field_to_ident])
                idxs = id_to_idx[key]
            for i in idxs:
                items_info[i][model_name] = model


class WildberriesIncrementItemScraper(WildberriesItemBase):
    def __init__(self):
        super().__init__()

    def update_from_mp(self, start_from: int = None) -> int:
        start = time.time()
        connection.close()
        if start_from is None:
            start_from = self.get_last_parsed_id()
        if start_from < self.config.max_item_id:
            max_item_id = self.config.max_item_id
        else:
            max_item_id = self._get_max_item_id()
            logger.info(f'New upper bound found: {max_item_id}')

        indexes_to_request = list(range(start_from, min(max_item_id + 1, start_from + self.config.bulk_item_step)))
        if len(indexes_to_request) == 0:
            return -1
        items_result = self.get_item_or_seller_info(indexes_to_request, self.config.items_api_url, ';', )
        sellers_result = self.get_item_or_seller_info(indexes_to_request,
                                                      self.config.seller_url, ',', is_special_header=True)

        if items_result['state'] == 0 and sellers_result['resultState'] == 0 and items_result['data']['products']:
            seller_id_to_name = {i['cod1S']: i['supplierName'] for i in sellers_result['value']}
            for item in items_result['data']['products']:
                item['sellerName'] = seller_id_to_name.get(item['id'])
            self.add_items_to_db(items_result['data']['products'])
        elif items_result['state'] == 0 and items_result['data']['products']:
            logger.warning(f'Error result in {start_from}: {sellers_result}')
            self.add_items_to_db(items_result['data']['products'])
        elif items_result['state'] == 0 and not items_result['data']['products']:
            logger.info(f'Items response is empty: {items_result}')
        else:
            logger.warning(f'Error result in {start_from}: {items_result}')

        logger.info(f'{start_from} elapsed {(time.time() - start):0.0f} seconds')
        return 0

    @staticmethod
    def get_last_parsed_id():
        return Item.objects.aggregate(Max('marketplace_id'))['marketplace_id__max']

    def _get_max_item_id(self) -> int:
        try:
            latest = Item.objects.latest('marketplace_id').marketplace_id
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
        result = self.get_item_or_seller_info(indexes_to_request, self.config.items_api_url, ';')

        # Find roughly lower and upper bounds
        while result['state'] == 0:
            latest += step_size
            indexes_to_request = [latest, latest + step_size]
            result = self.get_item_or_seller_info(indexes_to_request, self.config.items_api_url, ';')
        return latest, latest + step_size

    def _get_max_in_bounds(self, min_id: int, max_id: int) -> int:
        middle = ((max_id - min_id) // 2) + min_id

        if middle == min_id:
            return middle
        else:
            indexes_to_request = [min_id, middle]
            result = self.get_item_or_seller_info(indexes_to_request, self.config.items_api_url, ';')
            if result['state'] == 0:
                return self._get_max_in_bounds(middle + 1, max_id)
            else:
                return self._get_max_in_bounds(min_id, middle - 1)


class IncrementItemUpdaterProcessPool(WildberriesProcessPool):
    def __init__(self, scraper: WildberriesBaseScraper, cpu_multiplayer: Union[int, None] = 1):
        super().__init__(scraper, cpu_multiplayer)

    def start_process_pool(self):
        marketplace_id_max = WildberriesIncrementItemScraper().get_last_parsed_id()
        last_parsed = 1 if marketplace_id_max is None else marketplace_id_max

        with multiprocessing.Pool(processes=self.processes) as pool:
            while True:
                try:
                    if self.busy_processes < self.processes:
                        start_from = last_parsed
                        last_parsed += self.scraper.config.bulk_item_step
                        pool.apply_async(self.scraper.update_from_mp, args=(start_from,),
                                         callback=self._busy_processes_reducer, error_callback=self._stop_processes)
                        self.busy_processes += 1

                        if self.stop_processes:
                            logger.info(f'Multiprocessing pool stopping. Got result code -1')
                            break
                    else:
                        # For the sake of not wasting CPU powers too much
                        time.sleep(0.3)
                except KeyboardInterrupt:
                    break


class WildberriesItemInCategoryScraper(WildberriesItemBase):
    def __init__(self):
        super().__init__()
        logger.debug(f'Start check parse times')
        self._check_parse_times()
        logger.debug(f'Stop check parse times')
        self.lock = multiprocessing.Manager().Lock()

    @staticmethod
    def _check_parse_times():
        leaves = ItemCategory.objects.filter(Q(start_parse_time__isnull=False) | Q(next_parse_time__isnull=True),
                                             children__isnull=True)
        current_time = now()
        for leaf in leaves:
            leaf.start_parse_time = None
            leaf.next_parse_time = current_time
        ItemCategory.objects.bulk_update(leaves, ['start_parse_time', 'next_parse_time'])

    @staticmethod
    def _check_next_parse_time():
        leaves = ItemCategory.objects.filter(children__isnull=True, next_parse_time__isnull=False)
        for leaf in leaves:
            leaf.next = None
        ItemCategory.objects.bulk_update(leaves, ['start_parse_time'])

    def update_from_mp(self, start_from: int = None) -> int:
        start = time.time()
        connection.close()
        category_leaf = self._get_category_leave()
        if category_leaf is None:
            return -1
        logger.debug(f'Start update from mp for {category_leaf}')
        self._process_all_pages(category_leaf)
        logger.info(f'{category_leaf} elapsed {(time.time() - start):0.0f} seconds')
        return 0

    def _get_category_leave(self) -> ItemCategory:
        with transaction.atomic():
            start = time.time()
            num_items = ItemCategory.objects.exclude(children__isnull=False).filter(
                marketplace_source=self.marketplace_source, is_deleted=False,
                start_parse_time__isnull=True, next_parse_time__lte=now()).count()
            logger.debug(f'Remained {num_items} operation elapsed {time.time()-start:0.2f}')

            leaf = ItemCategory.objects.select_for_update(skip_locked=True).exclude(children__isnull=False).filter(
                marketplace_source=self.marketplace_source, is_deleted=False,
                start_parse_time__isnull=True, next_parse_time__lte=now()).first()
            if leaf is not None:
                leaf.start_parse_time = now()
                leaf.save()
                return leaf

    def _process_all_pages(self, category_leaf: ItemCategory):
        counter = 1
        while True:
            page_num = f'?page={counter}'
            bs, _, status_code = self.connector.get_page(RequestBody(category_leaf.marketplace_category_url + page_num,
                                                                     'get'))
            if status_code == 404 or self._is_items_not_found(bs, category_leaf):
                category_leaf.next_parse_time = now() + category_leaf.parse_frequency
                category_leaf.start_parse_time = None
                category_leaf.save()
                break
            else:
                logger.debug(f'\tPage number {counter} for {category_leaf}')
                self._process_items_on_page(bs, category_leaf)
            counter += 1

    @staticmethod
    def _is_items_not_found(bs: BeautifulSoup, category_leaf: ItemCategory) -> bool:
        all_items = bs.find('div', class_='catalog_main_table')
        if all_items is None:
            all_items = bs.find('div', id='divGoodsNotFound')
            if all_items is not None:
                logger.info(f'Empty category {category_leaf}')
            else:
                logger.error(f'Something is wrong while getting divGoodsNotFound for {category_leaf}')
            return True
        else:
            return False

    def _process_items_on_page(self, bs: BeautifulSoup, category_leaf: ItemCategory):
        all_items = bs.find('div', class_='catalog_main_table').findAll('div', class_='dtList')
        item_ids, img_id_to_objs, img_link_to_ids = self._extract_ids_imgs_from_page(all_items)

        self.lock.acquire()
        imgs_filtered = Image.objects.filter(marketplace_link__in=img_link_to_ids.keys())
        filtered_imgs_ids = []
        for img_filtered in imgs_filtered:
            item_id = img_link_to_ids[img_filtered.marketplace_link]
            img_id_to_objs[item_id] = img_filtered
            filtered_imgs_ids.append(item_id)

        new_imgs = Image.objects.bulk_create(
            [img for marketplace_id, img in img_id_to_objs.items() if marketplace_id not in filtered_imgs_ids])
        self.lock.release()

        for new_img in new_imgs:
            item_id = img_link_to_ids[new_img.marketplace_link]
            img_id_to_objs[item_id] = new_img

        available_items = Item.objects.filter(marketplace_id__in=item_ids)
        updated_ids = self._add_category_and_imgs(available_items, category_leaf,
                                                  img_id_to_objs) if available_items else set()
        not_in_db_ids = set(item_ids) - updated_ids

        item_json = self.get_item_or_seller_info(list(not_in_db_ids), self.config.items_api_url, ';')
        if item_json['state'] == 0:
            new_items = self.add_items_to_db(item_json['data']['products'])
            self._add_category_and_imgs(new_items, category_leaf, img_id_to_objs)
        else:
            logger.warning(f'Got bad response for items: {item_json}')

    @staticmethod
    def _add_category_and_imgs(items: List[Item], category_leaf: ItemCategory,
                               item_imgs: Dict[int, Image]) -> Set[int]:
        updated_ids = set()
        for item in items:
            item.categories.add(category_leaf)
            item.images.add(item_imgs[item.marketplace_id])
            updated_ids.add(item.marketplace_id)
        return updated_ids

    def _extract_ids_imgs_from_page(self, all_items: List[Tag]) -> Tuple[List[int], Dict[int, Image], Dict[str, int]]:
        marketplace_ids, imgs, link_to_ids = [], {}, {}
        for item in all_items:
            for tag in item.findAll('img'):
                try:
                    link = tag['src']
                except AttributeError:
                    continue
                if 'blank' not in link:
                    img_link = 'https:' + link
                    img_obj = Image(marketplace_link=img_link, marketplace_source=self.marketplace_source,
                                    next_parse_time=now())
                    imgs[int(item['data-popup-nm-id'])] = img_obj
                    link_to_ids[img_link] = int(item['data-popup-nm-id'])
                    marketplace_ids.append(int(item['data-popup-nm-id']))
                    break
        return marketplace_ids, imgs, link_to_ids


class WildberriesIndividualItemCategoryScraper(WildberriesBaseScraper):
    def update_from_mp(self, start_from: int = None) -> int:
        start = time.time()
        connection.close()
        item = self._get_item_to_update()
        if item is not None:
            self._individual_item_update(item)
            logger.debug(f'Done in {time.time() - start:0.0f} seconds')
        else:
            return -1
        return 0

    def _get_item_to_update(self) -> Item:
        with transaction.atomic():
            item = Item.objects.select_for_update(skip_locked=True).exclude(categories__isnull=False).filter(
                marketplace_source=self.marketplace_source, items_start_parse_time__isnull=True, is_deleted=False,
                no_individual_category=False).first()
            if item:
                self._update_start_parse_time(item)
                return item

    @staticmethod
    def _update_start_parse_time(item: Item) -> None:
        item.items_start_parse_time = now()
        item.save()

    def _individual_item_update(self, item: Item):
        item_bs, is_captcha, status_code = self.connector.get_page(RequestBody(
            self.config.individual_item_url.format(item.marketplace_id), 'get'))
        item.items_start_parse_time = None
        if status_code == 200:
            category = self._parse_category(item_bs)
            if category is not None:
                logger.debug(f'{category.name} set to {item.name}')
                item.categories.add(category)
            else:
                logger.info(f"Can't find category for item name = {item.name} "
                            f"and marketplace_id = {item.marketplace_id}")
                item.no_individual_category = True
        else:
            item.is_deleted = True
            logger.info(f'item {item.marketplace_id} is not used anymore')
        item.save()

    def _parse_category(self, item_bs: BeautifulSoup) -> ItemCategory:
        list_of_breadcrumbs = item_bs.find('ul', class_="bread-crumbs")
        if list_of_breadcrumbs is not None:
            descendant_name, parent_name, parent_parent_name = '', '', ''
            for tag in reversed(list_of_breadcrumbs.findAll('li', class_="breadcrumbs-item secondary")):
                if 'brands' not in tag.find('a')['href']:
                    if descendant_name == '':
                        descendant_name = tag.find('a').text.strip('\n')
                    elif parent_name == '':
                        parent_name = tag.find('a').text.strip('\n')
                    elif parent_parent_name == '':
                        parent_parent_name = tag.find('a').text.strip('\n')
                    else:
                        break
            return self._get_category_from_name(descendant_name, parent_name, parent_parent_name)

    @staticmethod
    def _get_category_from_name(name: str, parent: str, parent_parent: str) -> ItemCategory:
        if name != '':
            params = {'name': name.lower()}
            if parent != '':
                params['parent__name'] = parent.lower()
                if parent_parent != '':
                    params['parent__parent__name'] = parent_parent.lower()
            try:
                return ItemCategory.objects.get(**params)
            except ItemCategory.DoesNotExist as e:
                logger.error(f'Item Category does not exist: {e}')
        else:
            logger.error(f'No category name sent to function: {name}, {parent}, {parent_parent}')

        # Consider catching Multiple Object Return Error
