from django.core.management.base import BaseCommand

from core.utils.logging_helpers import get_logger
from core.utils.query_profiler import start_profiler

logger = get_logger()


class Command(BaseCommand):
    help = 'Start workers'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        start_profiler()
