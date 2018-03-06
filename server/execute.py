# Run the workflow, generating table output

from server.models import Workflow, Module, WfModule, ParameterVal
from server.models.StoredObject import *
from server.dispatch import module_dispatch_render
from django.db import transaction
from server.websockets import *
import pandas as pd
import numpy as np


# Tell client to reload (we've finished rendering)
def notify_client_workflow_version_changed(workflow):
    ws_client_rerender_workflow(workflow)


# Return the output of a particular module. Gets from cache if possible
def execute_wfmodule(wfmodule, nocache=False):
    table = pd.DataFrame()
    workflow = wfmodule.workflow
    target_rev = workflow.revision()

    # Start from the top, re-rendering any modules which do not have a cache at the current revision
    # Assumes not possible to have later revision cache after a module which has an earlier revision cache
    # (i.e. module stack always rendered in order)
    # If everything is rendered already, this will just return the cache
    for wfm in workflow.wf_modules.all():

        # Get module output from cache, if available and desired
        cache = None
        if not nocache:
            try:
                cache = StoredObject.objects.get(wf_module=wfm, type=StoredObject.CACHED_TABLE, metadata=target_rev)
            except StoredObject.DoesNotExist:
                pass

        # if we did not find an available cache, render
        if cache is None:
            # previous revisions are dead to us now (well, maybe good for undo, but we can re-render)
            StoredObject.objects.filter(wf_module=wfm, type=StoredObject.CACHED_TABLE).delete()
            table = module_dispatch_render(wfm, table)
            StoredObject.create_table(wfm, StoredObject.CACHED_TABLE, table, metadata=target_rev)
        else:
            table = cache.get_table()

        # found the module we were looking for, all done
        if wfm == wfmodule:
            break

    return table


# shortcut to execute without cache, handy for testing
def execute_nocache(wfm):
    return execute_wfmodule(wfm, nocache=True)

