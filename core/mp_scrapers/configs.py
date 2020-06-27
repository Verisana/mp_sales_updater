from core.types import ScraperConfigs


WILDBERRIES_CONFIG = ScraperConfigs(
    categories_url='https://www.wildberries.ru/menu/getrendered?lang=ru&burger=true',
    item_url='https://nm-2-card.wildberries.ru/enrichment/v1/api?&nm={}',
    revision_url='https://nm-2-card.wildberries.ru/enrichment/v1/api?&nm={}',
    use_proxy=False,
)
