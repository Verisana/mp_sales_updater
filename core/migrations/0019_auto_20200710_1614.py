# Generated by Django 3.0.7 on 2020-07-10 11:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_auto_20200710_1330'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='image_file',
            field=models.ImageField(blank=True, upload_to='image_model_storage/'),
        ),
    ]
