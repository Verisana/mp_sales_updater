# Generated by Django 3.0.7 on 2020-07-09 15:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_auto_20200707_2255'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='item',
            name='last_parsed_time',
        ),
        migrations.AddField(
            model_name='item',
            name='next_parsed_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
