from datetime import timedelta

from django.db import models
from mptt.models import MPTTModel, TreeForeignKey


class StandardFields(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CommonNameSourceId(StandardFields):
    name = models.CharField(max_length=128, blank=True, db_index=True)
    marketplace_id = models.IntegerField(blank=True, null=True, db_index=True)
    marketplace_source = models.ForeignKey('Marketplace', on_delete=models.PROTECT)

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.name} ({self.marketplace_source.name})'


class Marketplace(StandardFields):
    name = models.CharField(max_length=128, unique=True)
    working_schemes = models.ManyToManyField('MarketplaceScheme')

    def __str__(self):
        return self.name


class MarketplaceScheme(StandardFields):
    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name


class Item(StandardFields):
    name = models.CharField(max_length=256)
    marketplace_id = models.IntegerField(db_index=True)
    root_id = models.IntegerField(blank=True, null=True)
    marketplace_source = models.ForeignKey('Marketplace', on_delete=models.PROTECT, related_name='items')
    categories = models.ManyToManyField('ItemCategory', blank=True, related_name='items')
    images = models.ManyToManyField('Image', blank=True, related_name='items')
    seller = models.ForeignKey('Seller', on_delete=models.SET_NULL, blank=True, null=True, related_name='items')
    brand = models.ForeignKey('Brand', on_delete=models.SET_NULL, blank=True, null=True, related_name='items')
    colours = models.ManyToManyField('Colour', blank=True, related_name='items')
    size_name = models.CharField(max_length=128, blank=True, null=True)
    size_orig_name = models.CharField(max_length=128, blank=True, null=True)
    is_digital = models.BooleanField(default=False)
    is_adult = models.BooleanField(default=False)

    items_parse_frequency = models.DurationField(default=timedelta(days=7))
    items_next_parse_time = models.DateTimeField(null=True, blank=True, db_index=True)
    items_start_parse_time = models.DateTimeField(null=True, blank=True, db_index=True)

    revisions_parse_frequency = models.DurationField(default=timedelta(hours=24))
    revisions_next_parse_time = models.DateTimeField(null=True, blank=True, db_index=True)
    revisions_start_parse_time = models.DateTimeField(null=True, blank=True, db_index=True)

    is_deleted = models.BooleanField(default=False, db_index=True)

    # This flag is needed because we can't select FOR UPDATE from ManyToMany field with left outer join
    is_categories_filled = models.BooleanField(default=False, db_index=True)

    no_individual_category = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        try:
            return f'{self.name} ({self.marketplace_id}) {self.brand.name}'
        except AttributeError:
            return f'{self.name} ({self.marketplace_id})'

    def get_latest_revision(self):
        return self.item_revisions.last()


class ItemRevision(StandardFields):
    item = models.ForeignKey('Item', on_delete=models.PROTECT, related_name='item_revisions')

    rating = models.FloatField(default=0.0)
    comments_num = models.IntegerField(default=0)
    is_new = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)

    price = models.IntegerField()
    sale_price = models.IntegerField()
    available_qty = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'Revision_' + str(self.id) + ' ' + self.item.name


class ItemCategory(MPTTModel, StandardFields):
    name = models.CharField(max_length=128)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    marketplace_source = models.ForeignKey('Marketplace', on_delete=models.PROTECT)
    marketplace_id = models.IntegerField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    marketplace_category_url = models.CharField(max_length=256, blank=True)

    parse_frequency = models.DurationField(default=timedelta(days=7))
    next_parse_time = models.DateTimeField(null=True, blank=True)
    start_parse_time = models.DateTimeField(null=True, blank=True)

    is_leaf = models.BooleanField(default=False)

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name_plural = 'item categories'

    def __str__(self):
        return self.name


class Image(StandardFields):
    image_file = models.ImageField(upload_to='image_model_storage/', blank=True)
    marketplace_link = models.CharField(max_length=256, unique=True, db_index=True)
    marketplace_source = models.ForeignKey('Marketplace', on_delete=models.PROTECT)

    parse_frequency = models.DurationField(default=timedelta(days=7))
    next_parse_time = models.DateTimeField(null=True, blank=True, db_index=True)
    start_parse_time = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self):
        return self.marketplace_link


class Brand(CommonNameSourceId):
    pass


class Colour(CommonNameSourceId):
    pass


class Seller(CommonNameSourceId):
    pass
