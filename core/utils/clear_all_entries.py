from core.models import Item, ItemRevision, Colour, Brand, Image, Seller


def delete_all_entries():
    Item.objects.all().delete()
    ItemRevision.objects.all().delete()
    Colour.objects.all().delete()
    Image.objects.all().delete()
    Brand.objects.all().delete()
    Seller.objects.all().delete()