# Generated by Django 2.0.1 on 2018-01-09 17:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0004_auto_20180107_2022'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxon',
            name='english_name',
            field=models.CharField(db_index=True, max_length=1024, null=True),
        ),
        migrations.AlterField(
            model_name='taxon',
            name='parent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='viewer.Taxon'),
        ),
    ]
