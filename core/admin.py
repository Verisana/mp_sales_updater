from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from .models import Marketplace, MarketplaceScheme, Item, Brand, ItemCategory, ItemColour, ItemImage, \
                    ItemRevision, ItemSeller, ItemSize


class ModelAdminAllFieldsMixin(object):
    def __init__(self, model, admin_site):
        excluded = ['id', 'created_at', 'modified_at']
        self.list_display = [field.name for field in model._meta.fields]
        self.fields = [field.name for field in model._meta.fields if field.name not in excluded]
        self.save_on_top = True
        super(ModelAdminAllFieldsMixin, self).__init__(model, admin_site)


@admin.register(Brand)
class BrandAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(Marketplace)
class MarketplaceAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(MarketplaceScheme)
class MarketplaceSchemeAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(Item)
class ItemAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(ItemCategory)
class ItemCategoryAdmin(MPTTModelAdmin):
    pass


@admin.register(ItemColour)
class ItemColourAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(ItemImage)
class ItemImageAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(ItemRevision)
class ItemRevisionAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(ItemSeller)
class ItemSellerAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


@admin.register(ItemSize)
class ItemSizeAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass
