# Generated by Django 3.0.7 on 2020-07-07 17:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_auto_20200707_2245'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='image_file',
            field=models.ImageField(blank=True, default=None, upload_to='item/'),
            preserve_default=False,
        ),
    ]