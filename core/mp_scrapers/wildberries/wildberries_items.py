import time
from typing import List, Dict, Tuple
from itertools import product
from datetime import timedelta

from django.utils.timezone import now

from core.mp_scrapers.configs import WILDBERRIES_CONFIG
from core.utils.connector import Connector
from core.types import RequestBody
from core.models import Marketplace, MarketplaceScheme, ItemCategory, Item, Brand, \
                        Colour, Size, ItemImage


class WildberriesItemScraper:
    def __init__(self):
        self.config = WILDBERRIES_CONFIG
        self.connector = Connector(use_proxy=self.config.use_proxy)
        self.mp_source = self._get_mp_wb()

    def update_from_mp(self) -> None:
        self._increment_item_update(start_from=1)
        # self._in_category_update()

    def _get_mp_wb(self) -> Marketplace:
        scheme_qs = MarketplaceScheme.objects.get_or_create(name='FBM')[0]
        mp_wildberries, is_created = Marketplace.objects.get_or_create(name='Wildberries')
        if is_created:
            mp_wildberries.working_schemes.add(scheme_qs)
            mp_wildberries.save()
        return mp_wildberries

    def _increment_item_update(self, start_from: int = 1) -> None:
        #max_item_id = self._get_max_item_id()
        max_item_id = 13999999
        print(f'Upper bound found: {max_item_id}')

        start = time.time()
        for i in range(start_from, max_item_id+1, self.config.bulk_item_step):
            print(f'{i} elapsed {(time.time() - start):0.0f} seconds')
            start = time.time()

            indexes_to_request = list(map(str, range(i, min(max_item_id+1, i+self.config.bulk_item_step))))
            result = self._get_indexes_info(indexes_to_request)

            if result['state'] == 0:
                # noinspection PyTypeChecker
                for item in result['data']['products']:
                    self._add_items_to_db(item)
            else:
                print(f'Error result in {i}: {result}')

    def _get_indexes_info(self, indexes: List[str]) -> Dict:
        indexes = ';'.join(indexes)
        url = self.config.item_url.format(indexes)
        return self.connector.get_page(RequestBody(url, method='get', parsing_type='json'))

    def _get_max_item_id(self) -> int:
        try:
            latest = Item.objects.latest('mp_id').mp_id
        except Item.DoesNotExist as e:
            latest = 1

        if latest == 1:
            step_size = 5000000
        else:
            step_size = 100000
        lower, upper = self._get_rough_bounds(latest, step_size)
        return self._get_max_in_bounds(lower, upper)

    def _get_rough_bounds(self, latest: int, step_size: int) -> Tuple[int, int]:
        indexes_to_request = [str(latest), str(latest + step_size)]
        result = self._get_indexes_info(indexes_to_request)

        # Find roughly lower and upper bounds
        while result['state'] == 0:
            latest += step_size
            indexes_to_request = [str(latest), str(latest + step_size)]
            result = self._get_indexes_info(indexes_to_request)
        return latest, latest + step_size

    def _get_max_in_bounds(self, min_id: int, max_id: int) -> int:
        middle = ((max_id - min_id) // 2) + min_id

        if middle == min_id:
            return middle
        else:
            indexes_to_request = [str(min_id), str(middle)]
            result = self._get_indexes_info(indexes_to_request)
            if result['state'] == 0:
                return self._get_max_in_bounds(middle+1, max_id)
            else:
                return self._get_max_in_bounds(min_id, middle-1)

    def _add_items_to_db(self, item: Dict) -> None:
        brand, _ = Brand.objects.get_or_create(name=item['brand'], mp_source=self.mp_source, mp_id=item['brandId'])

        if len(item['colors']) > 0 and len(item['sizes']) > 0:
            for colour, size in product(item['colors'], item['sizes']):
                colour, _ = Colour.objects.get_or_create(name=colour['name'], mp_source=self.mp_source,
                                                         mp_id=colour['id'])
                size, _ = Size.objects.get_or_create(name=size['name'], orig_name=size['origName'],
                                                     mp_source=self.mp_source, mp_id=size['optionId'])
                self._create_item(item, brand, colour, size)
        elif len(item['colors']) > 0 and len(item['sizes']) == 0:
            for colour in item['colors']:
                colour, _ = Colour.objects.get_or_create(name=colour['name'], mp_source=self.mp_source,
                                                         mp_id=colour['id'])
                self._create_item(item, brand, colour=colour, size=None)
        elif len(item['colors']) == 0 and len(item['sizes']) > 0:
            for size in item['sizes']:
                size, _ = Size.objects.get_or_create(name=size['name'], orig_name=size['origName'],
                                                     mp_source=self.mp_source, mp_id=size['optionId'])
                self._create_item(item, brand, colour=None, size=size)
        elif len(item['colors']) == 0 and len(item['sizes']) == 0:
            self._create_item(item, brand, colour=None, size=None)

    def _create_item(self, item: Dict, brand: Brand, colour: Dict = None, size: Dict = None) -> None:
        last_parsed_time = now() - timedelta(days=1)
        new_item, _ = Item.objects.get_or_create(name=item['name'], mp_id=item['id'], root_id=item['root'],
                                                 mp_source=self.mp_source, brand=brand, colour=colour,
                                                 size=size)
        new_item.last_parsed_time = last_parsed_time
        new_item.save()

    def _in_category_update(self) -> None:
        category_leaves = self._get_category_leaves()

        for category_leave in category_leaves:
            request_info = None

    def _get_category_leaves(self) -> List[ItemCategory]:
        pass
