# Generated by Django 3.0.7 on 2020-07-17 07:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_auto_20200716_1958'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='item',
            name='colour',
        ),
        migrations.AddField(
            model_name='item',
            name='colour',
            field=models.ManyToManyField(blank=True, related_name='items', to='core.Colour'),
        ),
    ]
