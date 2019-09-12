# Generated by Django 2.2.5 on 2019-09-12 03:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finder', '0007_auto_20190912_0255'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genemodel',
            name='description',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='genemodel',
            name='fig_id',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='genemodel',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='genemodel',
            name='patric_id',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='genomemodel',
            name='genome_id',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='genomemodel',
            name='organism',
            field=models.CharField(max_length=1000),
        ),
    ]
