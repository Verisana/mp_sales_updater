# Generated by Django 3.0.7 on 2020-07-10 08:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_remove_itemrevision_discount'),
    ]

    operations = [
        migrations.RenameField(
            model_name='item',
            old_name='next_parsed_time',
            new_name='next_parse_time',
        ),
    ]