# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2019-01-02 00:01
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import server.models.module_version


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0025_reimport_modules'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='moduleversion',
            name='html_output',
        ),
        migrations.AlterField(
            model_name='moduleversion',
            name='spec',
            field=django.contrib.postgres.fields.jsonb.JSONField(validators=[server.models.module_version.validate_module_spec], verbose_name='spec'),
        ),
        migrations.AlterField(
            model_name='wfmodule',
            name='module_id_name',
            field=models.CharField(default='', max_length=200),
        ),
    ]