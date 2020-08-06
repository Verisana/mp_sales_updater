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
    def update_from_mp(self) -> int:
        start = time.time()
        connection.close()

        items, mp_ids = self._get_items_to_update()

        if len(mp_ids) > 0:
            items_info = self._get_items_info(mp_ids)
            self._check_wb_result_fullness(items_info, mp_ids)

            new_revisions = self._create_new_revisions(items_info, items)
            self._set_new_revisions_to_items(items, new_revisions)

        logger.debug(f'Done in {time.time() - start:0.0f} seconds')
        return 0

    def _get_items_to_update(self) -> Tuple[List[Item], List[int]]:
        with transaction.atomic():
            filtered_items_for_update = Item.objects.select_for_update(skip_locked=True).filter(
                is_deleted=False, mp_source=self.mp_source, revisions_next_parse_time__lte=now(),
                revisions_start_parse_time__isnull=True).order_by(
                'revisions_next_parse_time')[:self.config.bulk_item_step]

            for item in filtered_items_for_update:
                item.revisions_start_parse_time = now()
            Item.objects.bulk_update(filtered_items_for_update, ['revisions_start_parse_time'])

            return filtered_items_for_update, [item.mp_id for item in filtered_items_for_update]

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
            logger.error(f'Expected valid state from items_info {json_result}')

    @staticmethod
    def _check_wb_result_fullness(items_info: List[Dict], mp_ids: List[int]) -> None:
        assert len(items_info) == len(mp_ids)
        for item_info, mp_id in zip(items_info, mp_ids):
            assert item_info['id'] == mp_id

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
            item.revisions_next_parse_time = now() + item.revisions_parse_frequency
            item.revisions_start_parse_time = None
            items_to_update.append(item)
        Item.objects.bulk_update(items_to_update, ['latest_revision', 'revisions_next_parse_time',
                                                   'revisions_start_parse_time'])
