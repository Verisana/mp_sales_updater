import multiprocessing
import time
from abc import ABC, abstractmethod

from django.db import connection

from core.models import Marketplace, MarketplaceScheme
from core.mp_scrapers.configs import WILDBERRIES_CONFIG
from core.utils.connector import Connector


def get_mp_wb() -> Marketplace:
    scheme_qs = MarketplaceScheme.objects.get_or_create(name='FBM')[0]
    mp_wildberries, is_created = Marketplace.objects.get_or_create(name='Wildberries')
    if is_created:
        mp_wildberries.working_schemes.add(scheme_qs)
        mp_wildberries.save()
    return mp_wildberries


class WildberriesBaseScraper(ABC):
    connection.close()
    config = WILDBERRIES_CONFIG
    connector = Connector(use_proxy=config.use_proxy)
    mp_source = get_mp_wb()

    @abstractmethod
    def update_from_mp(self):
        raise NotImplementedError


class WildberriesProcessPool:
    def __init__(self, scraper: WildberriesBaseScraper, cpu_multiplier: int = 1):
        self.scraper = scraper
        self.cpu_count = multiprocessing.cpu_count()
        self.cpu_multiplier = cpu_multiplier

        # We can't have processes = 0
        self.processes = max(1, int(self.cpu_count * self.cpu_multiplier))
        self.current_processes = 0

    def start_process_pool(self):
        # start, end = 0, self.scraper.config.bulk_item_step
        # step = self.scraper.config.bulk_item_step

        with multiprocessing.Pool(processes=self.processes) as pool:
            while True:
                if self.current_processes < self.processes:
                    print('here')
                    pool.apply_async(self.scraper.update_from_mp, callback=self._current_processes_reducer,
                                     error_callback=self._current_processes_reducer)
                    self.current_processes += 1

                    # start += step
                    # end += step
                else:
                    # For the sake of not wasting CPU powers
                    time.sleep(0.3)

    def _current_processes_reducer(self):
        self.current_processes -= 1
