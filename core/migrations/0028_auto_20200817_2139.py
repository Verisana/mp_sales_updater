# Generated by Django 3.1 on 2020-08-17 16:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_auto_20200817_1844'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brand',
            name='marketplace_id',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='brand',
            name='name',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AlterField(
            model_name='colour',
            name='marketplace_id',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='colour',
            name='name',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AlterField(
            model_name='image',
            name='marketplace_link',
            field=models.CharField(db_index=True, max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='next_parse_time',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='start_parse_time',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='is_categories_filled',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='item',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='item',
            name='items_next_parse_time',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='items_start_parse_time',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='no_individual_category',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='item',
            name='revisions_next_parse_time',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='revisions_start_parse_time',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='seller',
            name='marketplace_id',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='seller',
            name='name',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
    ]
