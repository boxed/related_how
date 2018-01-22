# Generated by Django 2.0.1 on 2018-01-15 09:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Taxon',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wikidata_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('english_name', models.CharField(db_index=True, max_length=255, null=True)),
                ('parents_string', models.TextField()),
                ('rank', models.IntegerField(null=True)),
                ('parent', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='viewer.Taxon')),
            ],
        ),
    ]