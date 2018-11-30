# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0146_auto_20181129_1950'),
    ]

    operations = [
        # New Tab table
        migrations.CreateModel(
            name='Tab',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('position', models.IntegerField()),
                ('selected_wf_module_position', models.IntegerField(null=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['position'],
            },
        ),
        migrations.AddField(
            model_name='tab',
            name='workflow',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tabs', to='server.Workflow'),
        ),
        migrations.AddField(
            model_name='wfmodule',
            name='tab',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='wf_modules', to='server.Tab'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='workflow',
            name='selected_tab_position',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='reordermodulescommand',
            name='tab',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to='server.Tab'),
            preserve_default=False,
        ),
        migrations.RenameField(
            model_name='addmodulecommand',
            old_name='selected_wf_module',
            new_name='selected_wf_module_position',
        ),
    ]
