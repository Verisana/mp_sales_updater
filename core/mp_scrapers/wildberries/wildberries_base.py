import multiprocessing
import time
from abc import ABC, abstractmethod

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
    config = WILDBERRIES_CONFIG
    connector = Connector(use_proxy=config.use_proxy)
    mp_source = get_mp_wb()

    @abstractmethod
    def update_from_mp(self) -> None:
        raise NotImplementedError


class WildberriesProcessPool:
    def __init__(self, scraper: WildberriesBaseScraper, cpu_multiplier: int = 1):
        self.scraper = scraper
        self.cpu_count = multiprocessing.cpu_count()
        self.cpu_multiplier = cpu_multiplier

        # We can't have processes = 0
        self.processes = max(1, int(self.cpu_count * self.cpu_multiplier))
        self.busy_processes = 0

    def start_process_pool(self):
        with multiprocessing.Pool(processes=self.processes) as pool:
            while True:
                if self.busy_processes < self.processes:
                    pool.apply_async(self.scraper.update_from_mp, callback=self._busy_processes_reducer)
                    self.busy_processes += 1
                else:
                    # For the sake of not wasting CPU powers too much
                    time.sleep(0.3)

    def _busy_processes_reducer(self, result):
        self.busy_processes -= 1
