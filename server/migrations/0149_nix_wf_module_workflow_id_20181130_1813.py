# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0148_write_tabs_20181130_1407')
    ]

    operations = [
        migrations.RemoveField(
            model_name='workflow',
            name='selected_wf_module',
        ),
        migrations.AlterField(
            model_name='wfmodule',
            name='tab',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='tabs', to='server.Tab'),
        ),
        migrations.RemoveField(
            model_name='wfmodule',
            name='workflow',
        ),
    ]
