from django.core.management.base import BaseCommand, CommandError

from core.mp_scrapers.wildberries.wildberries_categories import WildberriesCategoryScraper
from core.mp_scrapers.wildberries.wildberries_images import WildberriesImageScraper
from core.mp_scrapers.wildberries.wildberries_items import WildberriesItemScraper
from core.mp_scrapers.wildberries.wildberries_revisions import WildberriesRevisionScraper
from core.mp_scrapers.wildberries.wildberries_base import WildberriesProcessPool


class Command(BaseCommand):
    help = 'Start workers'

    def add_arguments(self, parser):
        parser.add_argument('mp', type=str)
        parser.add_argument('type', type=str)
        parser.add_argument('--source', type=str)
        # parser.add_argument('--infinite', type=bool) TODO

    def handle(self, *args, **options):
        mp = options['mp'].lower()
        action_type = options['type'].lower()
        if mp == 'wildberries':
            if action_type == 'categories':
                scraper = WildberriesCategoryScraper()
                scraper.update_from_mp()
            elif action_type == 'items':
                scraper = WildberriesItemScraper()
                scraper.update_from_mp()
            elif action_type == 'revisions':
                scraper = WildberriesRevisionScraper()
                wb_process_pool = WildberriesProcessPool(scraper, cpu_multiplier=0)
                wb_process_pool.start_process_pool()
            elif action_type == 'images':
                scraper = WildberriesImageScraper()
                scraper.update_from_mp()
            else:
                raise CommandError(f"Unrecognized type {action_type} for marketplace {mp}")
        else:
            raise CommandError(f"Marketplace {mp} does not exist")
