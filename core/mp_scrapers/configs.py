from core.mp_scrapers.base import ScraperConfigs


WILDBERRIES_CONFIG = ScraperConfigs(
    categories_url='',
    item_url='https://nm-2-card.wildberries.ru/enrichment/v1/api?&nm={}',
    revision_url='https://nm-2-card.wildberries.ru/enrichment/v1/api?&nm={}',
    use_proxy=True,
    simultaneous_conn_limit=10
)
