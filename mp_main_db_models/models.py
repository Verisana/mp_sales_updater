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
    mp_id = None


class ItemSellers(models.Model):
    name = None
    mp_source = None
    created_at = None
    modified_at = None
    categories = None


class ItemBrands(models.Model):
    name = None
    mp_source = None
    mp_id = None

    created_at = None
    modified_at = None


class Items(models.Model):
    name = None
    mp_source = None
    categories = None
    seller = None
    mp_id = None
    root_id = None
    brand = None

    created_at = None
    modified_at = None

    last_update = None

    day_sales_speed = None



class ItemUpdates(models.Model):
    item = None
    created_at = None

    rating = None
    coments_num = None
    main_image = None
    is_new = None
    is_bestseller = None
    is_digital = None
    is_adult = None

    price = None
    sale_price = None
    available_qty = None