from django.contrib import admin

from .models import Marketplace, MarketplaceScheme, Item, ItemBrand, ItemCategory, ItemColour, ItemImage, \
                    ItemRevision, ItemSeller, ItemSize


class ModelAdminAllFieldsMixin(object):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields if field.name != "id"]
        self.fields = [field.name for field in model._meta.fields if field.name != "id"]
        save_on_top = True
        super(ModelAdminAllFieldsMixin, self).__init__(model, admin_site)


class MarketplaceAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


class MarketplaceSchemeAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


class ItemAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


class ItemBrandAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


class ItemCategoryAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


class ItemColourAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


class ItemImageAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


class ItemRevisionAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


class ItemSellerAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


class ItemSizeAdmin(ModelAdminAllFieldsMixin, admin.ModelAdmin):
    pass


admin.site.register(Marketplace, MarketplaceAdmin)
admin.site.register(MarketplaceScheme, MarketplaceSchemeAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(ItemBrand, ItemBrandAdmin)
admin.site.register(ItemCategory, ItemCategoryAdmin)
admin.site.register(ItemColour, ItemColourAdmin)
admin.site.register(ItemImage, ItemImageAdmin)
admin.site.register(ItemRevision, ItemRevisionAdmin)
admin.site.register(ItemSeller, ItemSellerAdmin)
admin.site.register(ItemSize, ItemSizeAdmin)
