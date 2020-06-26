from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Start listening for revision updates'

    def handle(self, *args, **options):
        pass
