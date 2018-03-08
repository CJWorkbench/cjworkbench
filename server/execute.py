# Run the workflow, generating table output

from server.models.StoredObject import *
from server.dispatch import module_dispatch_render
from server.websockets import *
from server.modules.urlscraper import urlscraper_execute_callbacks
import pandas as pd


# Tell client to reload (we've finished rendering)
def notify_client_workflow_version_changed(workflow):
    ws_client_rerender_workflow(workflow)

def get_render_cache(wfm, revision):
    # There can be more than one cached table for the same rev, if we did simultaneous renders
    # on two different threads. This is inefficient, but not harmful. So filter().first() not get()
    try:
        return StoredObject.objects.filter(wf_module=wfm,
                                            type=StoredObject.CACHED_TABLE,
                                            metadata=revision).first()
    except StoredObject.DoesNotExist:
        return None


# Return the output of a particular module. Gets from cache if possible
def execute_wfmodule(wfmodule, nocache=False):
    workflow = wfmodule.workflow
    target_rev = workflow.revision()

    # Do we already have what we need?
    cache = None
    if not nocache:
        cache = get_render_cache(wfmodule, target_rev)
    if cache:
        return cache.get_table()

    # No, let's render from the top, shortcutting with cache whenever possible
    table = pd.DataFrame()

    # Start from the top, re-rendering any modules which do not have a cache at the current revision
    # Assumes not possible to have later revision cache after a module which has an earlier revision cache
    # (i.e. module stack always rendered in order)
    # If everything is rendered already, this will just return the cache
    for wfm in workflow.wf_modules.all():

        # Get module output from cache, if available and desired
        cache = None
        if not nocache:
            cache = get_render_cache(wfm, target_rev)

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


# Resolve circular import: execute -> dispatch -> urlscraper -> execute
# So we create an object with callbacks in urlscraper, which we then fill out here
urlscraper_execute_callbacks.execute_wfmodule = execute_wfmodule
