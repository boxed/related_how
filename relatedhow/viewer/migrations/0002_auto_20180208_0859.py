# Generated by Django 2.0.1 on 2018-02-08 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taxon',
            name='name',
            field=models.CharField(db_index=True, max_length=255, null=True),
        ),
    ]