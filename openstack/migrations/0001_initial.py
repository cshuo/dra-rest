# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-05-11 09:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('holder', models.CharField(max_length=200)),
                ('log_type', models.CharField(max_length=200)),
                ('time', models.DateTimeField(verbose_name='date of log')),
                ('log_info', models.CharField(max_length=2000)),
            ],
        ),
    ]