# Generated by Django 3.0.7 on 2020-06-30 06:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_itemcategory_is_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemcategory',
            name='mp_category_url',
            field=models.CharField(blank=True, max_length=256),
        ),
    ]
