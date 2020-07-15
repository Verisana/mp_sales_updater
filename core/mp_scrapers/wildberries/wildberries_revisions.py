import time
from typing import List, Dict, Tuple, Generator

from django.db.models import QuerySet
from django.utils.timezone import now

from core.mp_scrapers.configs import WILDBERRIES_CONFIG
from core.utils.connector import Connector
from core.types import RequestBody
from core.models import Item, ItemRevision
from core.mp_scrapers.wildberries.wildberries_base import get_mp_wb


class WildberriesRevisionScraper:
    def __init__(self):
        self.config = WILDBERRIES_CONFIG
        self.connector = Connector(use_proxy=self.config.use_proxy)
        self.mp_source = get_mp_wb()

    def update_from_mp(self) -> None:
        items_gen = self._get_items_to_update()

        counter = 1
        start = time.time()
        for items, mp_ids in items_gen:
            items_info = self._get_items_info(mp_ids)
            assert len(items_info) == len(mp_ids)

            new_revisions = self._create_new_revisions(items_info, items)
            self._set_new_revisions_to_items(items, new_revisions)

            print(f'Done step {counter} in {time.time() - start:0.0f} seconds')
            counter += 1
            start = time.time()

    def _get_items_to_update(self) -> Generator[Tuple[List[Item], List[int]], None, None]:
        items_no_revision = Item.objects.filter(is_deleted=False, mp_source=self.mp_source,
                                                latest_revision__isnull=True)
        yield from self._chunk_items_iterator(items_no_revision)

        items_ready_to_parse = Item.objects.filter(is_deleted=False, mp_source=self.mp_source,
                                                   next_parsed_time__lte=now())
        yield from self._chunk_items_iterator(items_ready_to_parse)

    def _chunk_items_iterator(self, filtered_items: QuerySet) -> Generator[Tuple[List[Item], List[int]], None, None]:
        chunked_items, chunked_mp_ids = [], []
        for filtered_item in filtered_items.iterator():
            if len(chunked_items) < self.config.bulk_item_step:
                chunked_items.append(filtered_item)
                chunked_mp_ids.append(filtered_item.mp_id)
            else:
                yield chunked_items, chunked_mp_ids
                chunked_items.clear(), chunked_mp_ids.clear()

    def _get_items_info(self, indices: List[int]) -> List[Dict]:
        if len(indices) == 0:
            return []

        str_idxs = ';'.join(map(str, indices))
        url = self.config.items_api_url.format(str_idxs)
        json_result, *_ = self.connector.get_page(RequestBody(url, method='get', parsing_type='json'))

        if json_result['state'] == 0:
            items_info = json_result['data']['products']
            start_from = len(items_info)

            # Be careful. This implementation supposes items_info cut ONLY last queries
            # So, we linearly extend it to match our items
            items_info.extend(self._get_items_info(indices[start_from:]))
            return items_info
        else:
            print(f'Expected valid state from items_info {json_result}')

    def _create_new_revisions(self, items_info: List[Dict], items: List[Item]) -> List[ItemRevision]:
        new_revisions = []
        assert len(items_info) == len(items)
        for item_info, item in zip(items_info, items):
            available_qty = self._get_available_qty(item_info)
            price = item_info['price'] if item_info.get('price') else 0
            sale_price = item_info['salePrice'] if item_info.get('salePrice') else 0

            new_revision = ItemRevision(item=item, rating=item_info['rating'], comments_num=item_info['feedbackCount'],
                                        is_new=item_info['icons']['isNew'], price=price,
                                        sale_price=sale_price, available_qty=available_qty)
            new_revisions.append(new_revision)
        return ItemRevision.objects.bulk_create(new_revisions)

    @staticmethod
    def _get_available_qty(item_info: Dict) -> int:
        result = 0
        for size in item_info['sizes']:
            for stock in size['stocks']:
                result += stock['qty']
        return result

    @staticmethod
    def _set_new_revisions_to_items(items: List[Item], new_revisions: List[ItemRevision]) -> None:
        items_to_update = []
        assert len(new_revisions) == len(items)
        for revision, item in zip(new_revisions, items):
            item.latest_revision = revision
            item.next_parse_time = now() + item.parse_frequency
            items_to_update.append(item)
        Item.objects.bulk_update(items_to_update, ['latest_revision', 'next_parse_time'])
