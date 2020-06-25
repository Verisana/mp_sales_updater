from .base import ScraperConfigs, BaseScraper


WILDBERRIES_CONFIG = ScraperConfigs(
    categories_url='',
    item_url='',
    revision_url='',
)


class WildberriesScraper(BaseScraper):
    def __init__(self, use_proxy: bool=True):
        super().__init__((), ())
        self.urls = []
        self.proxies = []