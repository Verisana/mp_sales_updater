from django.db import models
from mptt.models import MPTTModel, TreeForeignKey


class Marketplace(models.Model):
    name = models.CharField(max_length=128, unique=True)
    working_schemes = models.ManyToManyField('MarketplaceScheme')

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class MarketplaceScheme(models.Model):
    name = models.CharField(max_length=128, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=256)
    mp_id = models.IntegerField()
    root_id = models.IntegerField(blank=True, null=True)
    mp_source = models.ForeignKey('Marketplace', on_delete=models.SET_NULL, null=True, related_name='item')
    categories = models.ManyToManyField('ItemCategory', related_name='item')
    seller = models.ForeignKey('ItemSeller', on_delete=models.SET_NULL, null=True, blank=True, related_name='item')
    brand = models.ForeignKey('ItemBrand', on_delete=models.SET_DEFAULT, default='_NO_BRAND_', related_name='item')
    colours = models.ManyToManyField('ItemColour', default='_NO_COLOURS_', related_name='item')
    sizes = models.ManyToManyField('ItemSize', default='_NO_SIZES_', related_name='item')
    images = models.ManyToManyField('ItemImage', blank=True, related_name='item')

    revision = models.ForeignKey('ItemRevision', on_delete=models.SET_NULL, null=True, blank=True, related_name='item')
    day_sales_speed = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ItemBrand(models.Model):
    name = models.CharField(max_length=128)
    mp_source = models.ForeignKey('Marketplace', on_delete=models.SET_NULL, null=True)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ItemCategory(MPTTModel):
    name = models.CharField(max_length=128)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    mp_source = models.ForeignKey('Marketplace', on_delete=models.SET_NULL, null=True)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name_plural = 'item categories'

    def __str__(self):
        return self.name


class ItemColour(models.Model):
    name = models.CharField(max_length=128)
    mp_source = models.ForeignKey('Marketplace', on_delete=models.SET_NULL, null=True)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ItemImage(models.Model):
    image = models.ImageField()

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.item


class ItemRevision(models.Model):
    rating = models.FloatField(default=0.0)
    comments_num = models.IntegerField(default=0)
    is_new = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)
    is_adult = models.BooleanField(default=False)

    price = models.IntegerField()
    sale_price = models.IntegerField()
    discount = models.IntegerField(default=0)
    available_qty = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.item


class ItemSeller(models.Model):
    name = models.CharField(max_length=128)
    mp_source = models.ForeignKey('Marketplace', on_delete=models.SET_NULL, null=True)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ItemSize(models.Model):
    name = models.CharField(max_length=128)
    mp_source = models.ForeignKey('Marketplace', on_delete=models.SET_NULL, null=True)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
