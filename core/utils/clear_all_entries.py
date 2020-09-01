from core.models import Item, ItemRevision, Colour, Brand, Image, Seller, ItemPosition


def delete_all_entries():
    print(ItemRevision.objects.all().delete())
    print(ItemPosition.objects.all().delete())
    print(Colour.objects.all().delete())
    print(Seller.objects.all().delete())
    print(Brand.objects.all().delete())
    print(Image.objects.all().delete())
    print(Item.objects.all().delete())
