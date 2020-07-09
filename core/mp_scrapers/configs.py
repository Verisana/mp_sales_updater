from core.types import ScraperConfigs


WILDBERRIES_CONFIG = ScraperConfigs(
    base_url='https://www.wildberries.ru',
    base_categories_url='https://www.wildberries.ru/menu/getrendered?lang=ru&burger=true',
    base_catalog_url='https://www.wildberries.ru/catalog/{}',
    items_api_url='https://nm-2-card.wildberries.ru/enrichment/v1/api?nm={}',
    individual_item_url='https://www.wildberries.ru/catalog/{}/detail.aspx',
    seller_url='https://lk.wildberries.ru/product/getsellers?ids={}',
    revision_url='https://nm-2-card.wildberries.ru/enrichment/v1/api?&nm={}',
    # Request size becomes too large to handle for big ids
    bulk_item_step=800,
    use_proxy=True,
)
