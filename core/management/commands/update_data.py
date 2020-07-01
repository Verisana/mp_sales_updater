from django.core.management.base import BaseCommand, CommandError
from core.mp_scrapers.wildberries.wildberries_categories import WildberriesCategoryScraper
from core.mp_scrapers.wildberries.wildberries_items import WildberriesItemScraper


class Command(BaseCommand):
    help = 'Start workers'

    def add_arguments(self, parser):
        parser.add_argument('mp', type=str)
        parser.add_argument('type', type=str)
        parser.add_argument('--source', type=str)

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
                pass
            else:
                raise CommandError(f"Unrecognized type {action_type} for marketplace {mp}")
        else:
            raise CommandError(f"Marketplace {mp} does not exist")
