from core.models import Item, ItemRevision, Colour, Brand, Image, Seller, ItemPosition


def delete_all_entries():
    item_revisions = ItemRevision.objects.all()
    print(item_revisions._raw_delete(item_revisions.db))

    item_positions = ItemPosition.objects.all()
    print(item_positions._raw_delete(item_positions.db))

    items = Item.objects.all()
    for item in items:
        item.colours.clear()
        item.categories.clear()
        item.images.clear()
    print(items._raw_delete(items.db))

    colours = Colour.objects.all()
    print(colours._raw_delete(colours.db))

    sellers = Seller.objects.all()
    print(sellers._raw_delete(sellers.db))

    brands = Brand.objects.all()
    print(brands._raw_delete(brands.db))

    images = Image.objects.all()
    print(images._raw_delete(images.db))
