# Generated by Django 3.1 on 2020-08-25 09:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_auto_20200817_2139'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemcategory',
            name='is_leaf',
            field=models.BooleanField(default=False),
        ),
    ]