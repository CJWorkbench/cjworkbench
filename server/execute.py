# Run the workflow, generating table output

from server.models import Workflow, Module, WfModule, ParameterVal
from server.models.StoredObject import *
from server.dispatch import module_dispatch_render
from django.db import transaction
from server.websockets import *
import pandas as pd
import numpy as np


# receive django channels background task start message
def execute_render_message_consumer(message):
    execute_render(message.workflow, message.rerender_from)

def execute_render(workflow, render_from=None):

    with transaction.atomic():
        wf_modules = workflow.wf_modules.all().order_by('order')
        revision = workflow.revision()

        if not wf_modules.exists():
            return None # nothing to render

        prev_wfm = render_from.previous_in_stack() if render_from is not None else None

        if prev_wfm is None:
            # start from top of stack if no module specified
            start_from = wf_modules.first()
            table = None
        else:
            # start from previously cached output of module previous to start_from module, if any
            try:
                cached_start = StoredObject.objects.get(wf_module=prev_wfm)
                start_from = render_from
                table = cached_start.get_table()
            except StoredObject.DoesNotExist:
                start_from = wf_modules.first()
                table = None

        # Main render loop
        started = False
        for wfm in wf_modules:
            if wfm == start_from:
                started = True

            if started:
                table = module_dispatch_render(wfm, table)
                StoredObject.create_table(wfm, StoredObject.CACHED_TABLE, table, metadata=revision)
            else:
                # if this module is before the changed one, then it doesn't need updating, so bump the rev on any cache
                try:
                    so = StoredObject.objects.get(wf_module = wfm)
                    so.metadata = revision
                    so.save()
                except StoredObject.DoesNotExist:
                    pass

    # We are done. Delete any tables from previously cached revisions of this workflow.
    # If everything works out right, there won't be any because we will have bumped all revisions. But.
    # (cannot delete inside transaction because rollback will cause inconsistency -- file will be missing)
    StoredObject.objects.filter(wf_module__workflow=workflow).exclude(metadata=revision).delete()

    # this is what ultimately triggers update on client
    notify_client_workflow_version_changed(workflow)


# Tell client to reload (we've finished rendering)
def notify_client_workflow_version_changed(workflow):
    ws_client_rerender_workflow(workflow)


# Return the output of a particular module. Super inefficient, deprecated
def execute_wfmodule(wfmodule):
    table = pd.DataFrame()
    workflow = wfmodule.workflow
    for wfm in workflow.wf_modules.all():
        table = module_dispatch_render(wfm, table)

        # don't ever give modules None, or return None. Empty table instead.
        if table is None:
            table = pd.DataFrame()

        if wfm == wfmodule:
            break


    return table




