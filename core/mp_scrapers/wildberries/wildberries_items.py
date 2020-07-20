import time
from collections import defaultdict
from typing import List, Dict, Tuple, Set, Union, Any, Callable, Generator

from bs4 import BeautifulSoup
from bs4.element import Tag
from django.db.models import Max
from django.db.models.base import ModelBase
from django.utils.timezone import now

from core.models import ItemCategory, Item, Brand, Colour, Image, Seller
from core.mp_scrapers.wildberries.wildberries_base import WildberriesBaseScraper
from core.types import RequestBody


class WildberriesItemScraper(WildberriesBaseScraper):
    xmlhttp_header: Dict[str, str]

    def __init__(self):
        self.xmlhttp_header = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/83.0.4103.116 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

    def update_from_mp(self) -> None:
        start_from = Item.objects.aggregate(Max('mp_id'))['mp_id__max']
        if start_from is None:
            start_from = 0

        self._increment_item_update(start_from)
        self._in_category_update()

    def _increment_item_update(self, start_from: int = 1) -> None:
        # max_item_id = self._get_max_item_id()
        max_item_id = 13999999
        print(f'Upper bound found: {max_item_id}')

        start = time.time()
        for i in range(start_from, max_item_id + 1, self.config.bulk_item_step):
            indexes_to_request = list(range(i, min(max_item_id + 1, i + self.config.bulk_item_step)))
            items_result = self._get_item_or_seller_info(indexes_to_request, self.config.items_api_url, ';', )
            sellers_result = self._get_item_or_seller_info(indexes_to_request,
                                                           self.config.seller_url, ',', is_special_header=True)

            if items_result['state'] == 0 and sellers_result['resultState'] == 0 and items_result['data']['products']:
                seller_id_to_name = {i['cod1S']: i['supplierName'] for i in sellers_result['value']}
                for item in items_result['data']['products']:
                    item['sellerName'] = seller_id_to_name.get(item['id'])
                self._add_items_to_db(items_result['data']['products'])
            elif items_result['state'] == 0 and items_result['data']['products']:
                print(f'Error result in {i}: {sellers_result}')
                self._add_items_to_db(items_result['data']['products'])
            elif not items_result['data']['products']:
                print(f'Items response is empty: {items_result}')
            else:
                print(f'Error result in {i}: {items_result}')

            print(f'{i} elapsed {(time.time() - start):0.0f} seconds')
            start = time.time()

            # For TESTING!!!!!!!!
            if i > start_from + (self.config.bulk_item_step * 10):
                break
            # !!!!!!!!!!!!!!!!!!!!!!!

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
        result = self._get_item_or_seller_info(indexes_to_request, self.config.items_api_url, ';')

        # Find roughly lower and upper bounds
        while result['state'] == 0:
            latest += step_size
            indexes_to_request = [latest, latest + step_size]
            result = self._get_item_or_seller_info(indexes_to_request, self.config.items_api_url, ';')
        return latest, latest + step_size

    def _get_max_in_bounds(self, min_id: int, max_id: int) -> int:
        middle = ((max_id - min_id) // 2) + min_id

        if middle == min_id:
            return middle
        else:
            indexes_to_request = [min_id, middle]
            result = self._get_item_or_seller_info(indexes_to_request, self.config.items_api_url, ';')
            if result['state'] == 0:
                return self._get_max_in_bounds(middle + 1, max_id)
            else:
                return self._get_max_in_bounds(min_id, middle - 1)

    def _get_item_or_seller_info(self, indices: List[int], url: str, sep: str, is_special_header: bool = False) -> Dict:
        indices = sep.join(map(str, indices))
        url = url.format(indices)
        headers = self.xmlhttp_header if is_special_header else None
        json_result, _, _ = self.connector.get_page(RequestBody(url,
                                                                method='get', parsing_type='json', headers=headers))
        return json_result

    def _add_items_to_db(self, items: List[Dict]) -> List[Item]:
        brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info = self._aggregate_info_from_items(items)

        self._fill_nones_in_items(brand_id_to_idx, items_info, Brand, 'brand', 'mp_id')
        self._fill_nones_in_items(colour_id_to_idx, items_info, Colour, 'colour', 'mp_id')
        self._fill_nones_in_items(seller_id_to_idx, items_info, Seller, 'seller', 'name')

        current_time = now()
        new_items, old_items, colours = [], [], []
        for item in items_info:
            create_params = {'name': item['name'], 'mp_id': item['mp_id'], 'mp_source': self.mp_source,
                             'root_id': item['root_id'], 'brand': item['brand'], 'size_name': item['size_name'],
                             'size_orig_name': item['size_orig_name'], 'seller': item['seller'],
                             'revisions_next_parse_time': current_time, 'is_digital': item['is_digital'],
                             'is_adult': item['is_adult']}
            get_params = {'mp_id': item['mp_id'], 'mp_source': self.mp_source}

            try:
                existing_item = Item.objects.get(**get_params)
                old_items.append(existing_item)
            except Item.DoesNotExist:
                new_item = Item(**create_params)
                try:
                    last_mp_id = new_items[-1].mp_id
                except IndexError:
                    last_mp_id = None
                if last_mp_id != new_item.mp_id:
                    new_items.append(new_item)
                    colours.append([item['colour'].pk])
                else:
                    colours[-1].append(item['colour'].pk)
            except Item.MultipleObjectsReturned:
                print(f'Something is wrong. You should get one object for params: {get_params}')
                continue

        if new_items:
            new_items = Item.objects.bulk_create(new_items)
            for new_item, colour_pks in zip(new_items, colours):
                new_item.colours.add(*colour_pks)
                self._individual_item_update(new_item)

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
                colour = {'name': ''}
                self._fill_objects(brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info, item, colour)
        return brand_id_to_idx, colour_id_to_idx, seller_id_to_idx, items_info

    def _fill_objects(self, brand_id_to_idx: Dict[Union[str, int], List[int]],
                      colour_id_to_idx: Dict[Union[str, int], List[int]],
                      seller_id_to_idx: Dict[Union[str, int], List[int]], items_info: List[Dict], item: Dict,
                      colour: Dict) -> None:
        new_item_info = {'name': item['name'], 'mp_id': item['id'], 'root_id': item['root'], 'brand': None,
                         'colour': None, 'size_name': '', 'size_orig_name': '', 'seller': None,
                         'is_digital': item['isDigital'], 'is_adult': item['isAdult']}
        if item['sizes']:
            new_item_info['size_name'] = item['sizes'][0]['name']
            new_item_info['size_orig_name'] = item['sizes'][0]['origName']
        items_info.append(new_item_info)

        brand_name = item.get('brand') if item.get('brand') is not None else ''
        brand_params = {'name': brand_name, 'mp_source': self.mp_source, 'mp_id': item.get('brandId')}
        self._prepare_model(items_info, brand_id_to_idx, Brand, brand_params, 'brand', 'mp_id')

        seller_name = item.get('sellerName') if item.get('sellerName') is not None else ''
        seller_params = {'name': seller_name, 'mp_source_id': self.mp_source.id}
        self._prepare_model(items_info, seller_id_to_idx, Seller, seller_params, 'seller', ['name', 'mp_source_id'])

        colour_name = colour.get('name') if colour.get('name') is not None else ''
        colour_params = {'name': colour_name, 'mp_source': self.mp_source, 'mp_id': colour.get('id')}
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

            # DEBUGGING !!!!!!!!!!!!!
            break
            # DEBUGGING !!!!!!!!!!!!!

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
        item_ids, img_id_to_objs, img_link_to_ids = self._extract_ids_imgs_from_page(all_items)

        imgs_filtered = Image.objects.filter(mp_link__in=img_link_to_ids.keys())
        filtered_imgs_ids = []
        for img_filtered in imgs_filtered:
            item_id = img_link_to_ids[img_filtered.mp_link]
            img_id_to_objs[item_id] = img_filtered
            filtered_imgs_ids.append(item_id)

        new_imgs = Image.objects.bulk_create(
            [img for mp_id, img in img_id_to_objs.items() if mp_id not in filtered_imgs_ids])

        for new_img in new_imgs:
            item_id = img_link_to_ids[new_img.mp_link]
            img_id_to_objs[item_id] = new_img

        available_items = Item.objects.filter(mp_id__in=item_ids)
        updated_ids = self._add_category_and_imgs(available_items, category_leaf,
                                                  img_id_to_objs) if available_items else set()
        not_in_db_ids = set(item_ids) - updated_ids

        item_json = self._get_item_or_seller_info(list(not_in_db_ids), self.config.items_api_url, ';')
        if item_json['state'] == 0:
            new_items = self._add_items_to_db(item_json['data']['products'])
            self._add_category_and_imgs(new_items, category_leaf, img_id_to_objs)
        else:
            print(f'Got bad response for items: {item_json}')

    @staticmethod
    def _add_category_and_imgs(items: List[Item], category_leaf: ItemCategory,
                               item_imgs: Dict[int, Image]) -> Set[int]:
        updated_ids = set()
        for item in items:
            item.categories.add(category_leaf)
            item.images.add(item_imgs[item.mp_id])
            updated_ids.add(item.mp_id)
        return updated_ids

    def _extract_ids_imgs_from_page(self, all_items: List[Tag]) -> Tuple[List[int], Dict[int, Image], Dict[str, int]]:
        mp_ids, imgs, link_to_ids = [], {}, {}
        for item in all_items:
            mp_ids.append(int(item['data-popup-nm-id']))

            img_link = 'https:'
            for tag in item.findAll('img'):
                try:
                    link = tag['src']
                except AttributeError:
                    continue
                if 'blank' not in link:
                    img_link += link
                    break
            img_obj = Image(mp_link=img_link, mp_source=self.mp_source, next_parse_time=now())
            if img_link != 'https:':
                imgs[int(item['data-popup-nm-id'])] = img_obj
                link_to_ids[img_link] = int(item['data-popup-nm-id'])
        return mp_ids, imgs, link_to_ids

    def _individual_item_update(self, item: Item):
        item_bs, is_captcha, status_code = self.connector.get_page(RequestBody(
            self.config.individual_item_url.format(item.mp_id), 'get'))
        if status_code == 200:
            category = self._parse_category(item_bs)
            if category is not None:
                print(f'{category.name} set to {item.name}')
                item.categories.add(category)
            else:
                print(f"Can't find category for item name = {item.name} and mp_id = {item.mp_id}")
        else:
            item.is_deleted = True
            item.save()
            print(f'item {item.mp_id} is not used anymore')

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
                print(f'Item Category does not exist: {e}')
        else:
            print(f'No category name sent to function: {name}, {parent}, {parent_parent}')

        # Consider catching Multiple Object Return Error
