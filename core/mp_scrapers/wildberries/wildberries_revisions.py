import asyncio
import time
from typing import List, Dict, Tuple

from django.db import connection, transaction
from django.utils.timezone import now

from core.models import Item, ItemRevision
from core.mp_scrapers.wildberries.wildberries_base import WildberriesBaseScraper
from core.types import RequestBody
from core.utils.logging_helpers import get_logger

logger = get_logger()


class WildberriesRevisionScraper(WildberriesBaseScraper):
    def update_from_mp(self, start_from: int = None) -> int:
        start = time.time()
        connection.close()

        items, marketplace_ids = self._get_items_to_update()

        if len(marketplace_ids) == 0:
            return -1

        items_info = self._get_items_info(marketplace_ids)
        self._execute_revision_update(items, items_info)
        logger.debug(f'Done in {time.time() - start:0.0f} seconds')
        return 0

    def update_from_args(self, items: List[Item], items_info: List[Dict]) -> int:
        start = time.time()
        connection.close()

        checked_items, checked_info = [], []
        for item, item_info in zip(items, items_info):
            if item.next_parse_time is None:
                item.next_parse_time = now()
                item.save()
            if item.next_parse_time <= now():
                checked_items.append(item)
                checked_info.append(item_info)

        if len(checked_items) == 0:
            return -1

        self._execute_revision_update(checked_items, checked_info)
        logger.debug(f'Revision update done in {time.time() - start:0.2f} sec.')
        return 0

    @staticmethod
    def check_items_fullness(items: List[Item], items_info: List[Dict]) -> None:
        assert len(items) == len(items_info)
        items_info.sort(key=lambda x: x['id'])
        items.sort(key=lambda x: x.marketplace_id)
        for item, item_info in zip(items, items_info):
            assert item.marketplace_id == item_info['id']

    def _execute_revision_update(self, items: List[Item], items_info: List[Dict]) -> None:
        self.check_items_fullness(items, items_info)
        new_revisions = self._create_new_revisions(items, items_info)
        self._update_revision_times(items, new_revisions)

    def _get_items_to_update(self) -> Tuple[List[Item], List[int]]:
        with transaction.atomic():
            filtered_items_for_update = Item.objects.select_related('marketplace_source').select_for_update(
                skip_locked=True).filter(
                is_deleted=False, marketplace_source=self.marketplace_source, next_parse_time__lte=now(),
                start_parse_time__isnull=True)[:self.config.bulk_item_step]

            for item in filtered_items_for_update:
                item.revisions_start_parse_time = now()
            Item.objects.bulk_update(filtered_items_for_update, ['start_parse_time'])

            return filtered_items_for_update, [item.marketplace_id for item in filtered_items_for_update]

    def _get_items_info(self, indices: List[int]) -> List[Dict]:
        if len(indices) == 0:
            return []

        str_idxs = ';'.join(map(str, indices))
        url = self.config.items_api_url.format(str_idxs)
        json_result, *_ = asyncio.run(self.connector.get_page(RequestBody(url, method='get', parsing_type='json')))

        if json_result['state'] == 0:
            items_info = json_result['data']['products']
            start_from = len(items_info)

            # Be careful. This implementation supposes items_info cut ONLY last queries
            # So, we linearly extend it to match our items
            items_info.extend(self._get_items_info(indices[start_from:]))
            return items_info
        else:
            logger.error(f'Expected valid state from items_info {json_result}')

    def _create_new_revisions(self, items: List[Item], items_info: List[Dict]) -> List[ItemRevision]:
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

    def _update_revision_times(self, items: List[Item], new_revisions: List[ItemRevision]) -> None:
        items_to_update = []
        assert len(new_revisions) == len(items)
        for revision, item in zip(new_revisions, items):
            item.next_parse_time = now() + self.config.revisions_parse_frequency
            item.start_parse_time = None
            items_to_update.append(item)
        Item.objects.bulk_update(items_to_update, ['next_parse_time',
                                                   'start_parse_time'])
