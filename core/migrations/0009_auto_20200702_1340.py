# Generated by Django 3.0.7 on 2020-07-02 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_auto_20200702_1225'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='items', to='core.ItemCategory'),
        ),
        migrations.AlterField(
            model_name='item',
            name='images',
            field=models.ManyToManyField(blank=True, related_name='items', to='core.Image'),
        ),
    ]
