# Generated by Django 2.0.1 on 2018-01-25 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxon',
            name='number_of_direct_and_indirect_children',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='taxon',
            name='number_of_direct_children',
            field=models.IntegerField(null=True),
        ),
    ]
