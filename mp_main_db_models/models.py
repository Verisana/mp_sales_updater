from django.db import models


class MarketPlaces(models.Model):
    name = None
    created_at = None
    modified_at = None
    working_scheme = None


class ItemCategories(models.Model):
    name = None
    mp_source = None
    created_at = None
    modified_at = None


class ItemSellers(models.Model):
    name = None
    mp_source = None
    created_at = None
    modified_at = None
    categories = None


class Items(models.Model):
    name = None
    mp_source = None
    categories = None
    seller = None
    sku = None
    brand = None

    created_at = None
    modified_at = None

    last_update = None


class ItemUpdates(models.Model):
    item = None
    created_at = None

    rating = None
    coments_num = None
    main_image = None
    is_new = None
    is_bestseller = None

    full_price = None
    discount = None
    available_qty = None
