from typing import List

from .utils.connector import Connector


class DatabaseManager:
    def __init__(self):
        pass


class RevisionUpdateManager:
    def __init__(self, mp_scrapers: List):
        self.mp_scrapers = mp_scrapers
        self.db_manager = DatabaseManager()

    def start(self):
        while True:
            for scraper in self.mp_scrapers:
                pass
