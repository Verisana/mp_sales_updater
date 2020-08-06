from django.core.management.base import BaseCommand, CommandError

from core.mp_scrapers.wildberries.wildberries_categories import WildberriesCategoryScraper
from core.mp_scrapers.wildberries.wildberries_images import WildberriesImageScraper
from core.mp_scrapers.wildberries.wildberries_items import WildberriesItemScraper, WildberriesItemCategoryScraper
from core.mp_scrapers.wildberries.wildberries_revisions import WildberriesRevisionScraper
from core.mp_scrapers.wildberries.wildberries_base import WildberriesProcessPool
from core.utils.logging_helpers import get_logger

logger = get_logger()


class Command(BaseCommand):
    help = 'Start workers'

    def add_arguments(self, parser):
        parser.add_argument('mp', type=str)
        parser.add_argument('type', type=str)
        parser.add_argument('--source_file', type=str)

    def handle(self, *args, **options):
        mp = options['mp'].lower()
        action_type = options['type'].lower()
        try:
            source_file = options.get('source').lower()
        except AttributeError:
            source_file = None
        try:
            if mp == 'wildberries':
                if action_type == 'categories':
                    scraper = WildberriesCategoryScraper()
                    if source_file:
                        scraper.update_from_file(source_file)
                    else:
                        scraper.update_from_mp()
                elif action_type == 'items_full':
                    scraper = WildberriesItemScraper()
                    scraper.update_from_mp()
                elif action_type == 'items_individual_category':
                    scraper = WildberriesItemCategoryScraper()
                    wb_process_pool = WildberriesProcessPool(scraper, cpu_multiplier=1)
                    wb_process_pool.start_process_pool()
                elif action_type == 'revisions':
                    scraper = WildberriesRevisionScraper()
                    wb_process_pool = WildberriesProcessPool(scraper, cpu_multiplier=1)
                    wb_process_pool.start_process_pool()
                elif action_type == 'images':
                    scraper = WildberriesImageScraper()
                    wb_process_pool = WildberriesProcessPool(scraper, cpu_multiplier=1)
                    wb_process_pool.start_process_pool()
                else:
                    raise CommandError(f"Unrecognized type {action_type} for marketplace {mp}")
            else:
                raise CommandError(f"Marketplace {mp} does not exist")
        except Exception as e:
            logger.exception(e)
            raise e
