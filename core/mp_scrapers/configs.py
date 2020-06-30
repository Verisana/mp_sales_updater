from core.types import ScraperConfigs


WILDBERRIES_CONFIG = ScraperConfigs(
    base_url='https://www.wildberries.ru',
    base_categories_url='https://www.wildberries.ru/menu/getrendered?lang=ru&burger=true',
    base_catalog_url='https://www.wildberries.ru/catalog/{}',
    item_url='https://nm-2-card.wildberries.ru/enrichment/v1/api?&nm={}',
    revision_url='https://nm-2-card.wildberries.ru/enrichment/v1/api?&nm={}',
    bulk_item_step=950,
    use_proxy=True,
)
