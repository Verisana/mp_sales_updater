# Generated by Django 3.0.7 on 2020-07-09 16:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_auto_20200709_2049'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='itemrevision',
            name='discount',
        ),
    ]