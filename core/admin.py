from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from .models import Marketplace, MarketplaceScheme, Item, ItemRevision, ItemCategory, Image, \
                    Brand, Colour, Seller


class ModelAdminAllFieldsMixin(object):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields]
        self.save_on_top = True
        super(ModelAdminAllFieldsMixin, self).__init__(model, admin_site)


@admin.register(Marketplace)
class MarketplaceAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    filter_horizontal = ('working_schemes',)


@admin.register(MarketplaceScheme)
class MarketplaceSchemeAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(Item)
class ItemAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    filter_horizontal = ('categories',)


@admin.register(ItemRevision)
class ItemRevisionAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(ItemCategory)
class ItemCategoryAdmin(ModelAdminAllFieldsMixin, MPTTModelAdmin):
    pass


@admin.register(Image)
class ItemImageAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(Brand)
class BrandAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(Colour)
class ColourAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(Seller)
class ItemSellerAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass
