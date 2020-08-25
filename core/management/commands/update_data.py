from typing import Dict, Union, Tuple

from django.core.management.base import BaseCommand, CommandError

from core.mp_scrapers.wildberries.wildberries_categories import WildberriesCategoryScraper
from core.mp_scrapers.wildberries.wildberries_images import WildberriesImageScraper
from core.mp_scrapers.wildberries.wildberries_items import WildberriesIndividualItemCategoryScraper, \
    WildberriesIncrementItemScraper, WildberriesItemInCategoryScraper, IncrementItemUpdaterProcessPool
from core.mp_scrapers.wildberries.wildberries_revisions import WildberriesRevisionScraper
from core.mp_scrapers.wildberries.wildberries_base import WildberriesProcessPool, WildberriesBaseScraper
from core.utils.logging_helpers import get_logger

logger = get_logger()


class Command(BaseCommand):
    help = 'Start workers'

    def add_arguments(self, parser):
        parser.add_argument('mp', type=str)
        parser.add_argument('type', type=str)
        parser.add_argument('--source_file', type=str)
        parser.add_argument('--cpu_multiplayer', type=int)

    def handle(self, *args, **options):
        mp, action_type, source_file, cpu_multiplayer = self._get_arguments(options)
        try:
            if mp == 'wildberries':
                wb_process_pool = None
                if action_type == 'categories':
                    scraper = WildberriesCategoryScraper()
                elif action_type == 'items_increment':
                    scraper = WildberriesIncrementItemScraper()
                    wb_process_pool = IncrementItemUpdaterProcessPool(scraper, cpu_multiplayer=cpu_multiplayer)
                elif action_type == 'items_in_category':
                    scraper = WildberriesItemInCategoryScraper()
                    wb_process_pool = WildberriesProcessPool(scraper, cpu_multiplayer=cpu_multiplayer)
                elif action_type == 'items_individual_category':
                    scraper = WildberriesIndividualItemCategoryScraper()
                    wb_process_pool = WildberriesProcessPool(scraper, cpu_multiplayer=cpu_multiplayer)
                elif action_type == 'revisions':
                    scraper = WildberriesRevisionScraper()
                    wb_process_pool = WildberriesProcessPool(scraper, cpu_multiplayer=cpu_multiplayer)
                elif action_type == 'images':
                    scraper = WildberriesImageScraper()
                    wb_process_pool = WildberriesProcessPool(scraper, cpu_multiplayer=cpu_multiplayer)
                else:
                    raise CommandError(f"Unrecognized type {action_type} for marketplace {mp}")
                if cpu_multiplayer == 0:
                    wb_process_pool = None
                self._start_worker(scraper, process_pool=wb_process_pool, source_file=source_file)
            else:
                raise CommandError(f"Marketplace {mp} does not exist")
        except Exception as e:
            logger.exception(e)
            raise e

    @staticmethod
    def _get_arguments(options: Dict) -> Tuple[str, str, Union[str, None], Union[int, None]]:
        mp = options['mp'].lower()
        action_type = options['type'].lower()
        source_file, cpu_multiplayer = None, None

        if isinstance(options.get('source_file'), str):
            source_file = options.get('source_file').lower()
        if isinstance(options.get('cpu_multiplayer'), int):
            cpu_multiplayer = options.get('cpu_multiplayer')

        return mp, action_type, source_file, cpu_multiplayer

    @staticmethod
    def _start_worker(scraper: Union[WildberriesBaseScraper, WildberriesCategoryScraper],
                      process_pool: WildberriesProcessPool = None, source_file: str = None):
        if process_pool:
            process_pool.start_process_pool()
        else:
            if source_file:
                scraper.update_from_file(source_file)
            else:
                scraper.update_from_mp()
