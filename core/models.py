from datetime import timedelta

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
    mp_source = models.ForeignKey('Marketplace', on_delete=models.CASCADE, related_name='items')
    categories = models.ManyToManyField('ItemCategory', related_name='items')
    seller = models.ForeignKey('Seller', on_delete=models.CASCADE, blank=True, null=True, related_name='items')
    brand = models.ForeignKey('Brand', on_delete=models.CASCADE, blank=True, null=True, related_name='items')
    colour = models.ForeignKey('Colour', on_delete=models.CASCADE, blank=True, null=True, related_name='items')
    size = models.ForeignKey('Size', on_delete=models.CASCADE, blank=True, null=True, related_name='items')

    latest_revision = models.OneToOneField('ItemRevision', on_delete=models.CASCADE,
                                           null=True, blank=True, related_name='items')

    parse_frequency = models.DurationField(default=timedelta(hours=24))
    last_parsed_time = models.DateTimeField(auto_now_add=True)

    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ItemRevision(models.Model):
    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='item_revisions')

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
        return 'Revision_' + str(self.id) + ' ' + self.item.name


class ItemCategory(MPTTModel):
    name = models.CharField(max_length=128)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    mp_source = models.ForeignKey('Marketplace', on_delete=models.CASCADE)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name_plural = 'item categories'

    def __str__(self):
        return self.name


class ItemImage(models.Model):
    image = models.ImageField(upload_to='item/')
    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='item_images')

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.image


class Brand(models.Model):
    name = models.CharField(max_length=128)
    mp_source = models.ForeignKey('Marketplace', on_delete=models.CASCADE)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Colour(models.Model):
    name = models.CharField(max_length=128)
    mp_source = models.ForeignKey('Marketplace', on_delete=models.CASCADE)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name + ' (' + self.mp_source.name + ')'


class Seller(models.Model):
    name = models.CharField(max_length=128)
    mp_source = models.ForeignKey('Marketplace', on_delete=models.CASCADE)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name + ' (' + self.mp_source.name + ')'


class Size(models.Model):
    name = models.CharField(max_length=128)
    mp_source = models.ForeignKey('Marketplace', on_delete=models.CASCADE)
    mp_id = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name + ' (' + self.mp_source.name + ')'
