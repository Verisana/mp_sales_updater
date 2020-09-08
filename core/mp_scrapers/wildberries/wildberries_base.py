import multiprocessing
import pickle
import time
from abc import ABC, abstractmethod
from typing import Union, Any

from core.models import Marketplace, MarketplaceScheme
from core.mp_scrapers.configs import WILDBERRIES_CONFIG
from core.utils.connector import Connector
from core.utils.logging_helpers import get_logger

logger = get_logger()


def get_mp_wb() -> Marketplace:
    scheme_qs = MarketplaceScheme.objects.get_or_create(name='FBM')[0]
    mp_wildberries, is_created = Marketplace.objects.get_or_create(name='Wildberries')
    if is_created:
        mp_wildberries.working_schemes.add(scheme_qs)
        mp_wildberries.save()
    return mp_wildberries


def save_object_for_logging(obj: Any, name: str, type: str = 'pickle') -> None:
    if type == 'pickle':
        with open(f'logs/{name}', 'wb') as file:
            pickle.dump(obj, file)
    elif type == 'string':
        with open(f'logs/{name}', 'w') as file:
            file.write(obj)
    else:
        logger.error(f'Wrong argument for function save_object_for_logging. Check all calls')


class WildberriesBaseScraper(ABC):
    config = WILDBERRIES_CONFIG
    connector = Connector(use_proxy=config.use_proxy)
    marketplace_source = get_mp_wb()

    @abstractmethod
    def update_from_mp(self, start_from: int = None) -> int:
        raise NotImplementedError


class WildberriesProcessPool:
    def __init__(self, scraper: WildberriesBaseScraper, cpu_multiplayer: Union[int, None] = 1):
        self.scraper = scraper
        self.cpu_count = multiprocessing.cpu_count()
        self.cpu_multiplier = 1 if cpu_multiplayer is None else cpu_multiplayer

        # We can't have processes = 0
        self.processes = max(1, int(self.cpu_count * self.cpu_multiplier))
        self.busy_processes = 0
        self.stop_processes = False
        self.last_error = None

    def start_process_pool(self):
        with multiprocessing.Pool(processes=self.processes) as pool:
            while True:
                try:
                    if self.busy_processes < self.processes:
                        pool.apply_async(self.scraper.update_from_mp, callback=self._busy_processes_reducer,
                                         error_callback=self._stop_processes)
                        self.busy_processes += 1
                    else:
                        # For the sake of not wasting CPU powers too much
                        time.sleep(0.3)

                    if self.stop_processes:
                        logger.info(f'Multiprocessing pool stopping. Got result code -1')
                        break
                except KeyboardInterrupt:
                    logger.info(f'Multiprocessing pool stopping. Got KeyboardInterrupt')
                    break

        if self.last_error is not None:
            raise self.last_error

    def _busy_processes_reducer(self, result: int):
        self.busy_processes -= 1
        if result == -1:
            self.stop_processes = True

    def _stop_processes(self, error):
        self.stop_processes = True
        self.last_error = error
