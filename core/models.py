from django.db import models


class MarketPlace(models.Model):
    name = None
    created_at = None
    modified_at = None
    working_scheme = None


class ItemCategory(models.Model):
    name = None
    mp_source = None
    mp_id = None

    created_at = None
    modified_at = None


class ItemSeller(models.Model):
    name = None
    mp_source = None
    categories = None

    created_at = None
    modified_at = None


class ItemBrand(models.Model):
    name = None
    mp_source = None
    mp_id = None

    created_at = None
    modified_at = None


class Item(models.Model):
    name = None
    mp_source = None
    category = None
    seller = None
    mp_id = None
    root_id = None
    brand = None

    revision = None
    day_sales_speed = None

    created_at = None
    modified_at = None


class ItemImage(models.Model):
    item = None
    item_revision = None
    image = None

    created_at = None
    modified_at = None


class ItemRevision(models.Model):
    item = None

    rating = None
    comments_num = None
    is_new = None
    is_bestseller = None
    is_digital = None
    is_adult = None

    price = None
    sale_price = None
    available_qty = None

    created_at = None
    modified_at = None
