from core.models import Marketplace, MarketplaceScheme


def get_mp_wb() -> Marketplace:
    scheme_qs = MarketplaceScheme.objects.get_or_create(name='FBM')[0]
    mp_wildberries, is_created = Marketplace.objects.get_or_create(name='Wildberries')
    if is_created:
        mp_wildberries.working_schemes.add(scheme_qs)
        mp_wildberries.save()
    return mp_wildberries
