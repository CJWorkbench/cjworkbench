# -*- coding: utf-8 -*-
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0147_add_tabs_pre_data'),
    ]

    operations = [
        migrations.RunSQL(["""
            DO $$
            BEGIN

            INSERT INTO server_tab
               (workflow_id, position, name, selected_wf_module_position,
                           is_deleted)
            SELECT id, 0, '', selected_wf_module, FALSE
            FROM server_workflow;

            UPDATE server_wfmodule
            SET tab_id = (
                SELECT tab.id
                FROM server_tab tab
                WHERE tab.workflow_id = server_wfmodule.workflow_id
                AND tab.position = 0
            );

            UPDATE server_reordermodulescommand
            SET tab_id = (
                SELECT tab.id
                FROM server_tab tab
                WHERE tab.workflow_id = (
                          SELECT workflow_id
                          FROM server_delta
                          WHERE id = server_reordermodulescommand.delta_ptr_id
                      )
                  AND tab.position = 0
            );

            END$$
        """]),
    ]
