from django.core.management.base import BaseCommand
from core.mp_scrapers.wildberries import WildberriesCategoryScraper


class Command(BaseCommand):
    help = 'Categories update worker'

    def handle(self, *args, **options):
        wb = WildberriesCategoryScraper()
        wb.update_categories()