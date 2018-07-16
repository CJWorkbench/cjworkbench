# Run the workflow, generating table output

from server.models.StoredObject import StoredObject
from server.dispatch import module_dispatch_render
from server.websockets import ws_client_rerender_workflow
from server.modules.types import ProcessResult


# Tell client to reload (we've finished rendering)
def notify_client_workflow_version_changed(workflow):
    ws_client_rerender_workflow(workflow)


def get_render_cache(wfm, revision):
    # There can be more than one cached table for the same rev, if we did
    # simultaneous renders on two different threads. This is inefficient, but
    # not harmful. So filter().first() not get()
    obj = wfm.stored_objects.filter(type=StoredObject.CACHED_TABLE,
                                    metadata=revision).first()
    if obj is None:
        return None

    table = obj.get_table()
    return ProcessResult(table, error=wfm.error_msg)


# Return the output of a particular module. Gets from cache if possible
def execute_wfmodule(wfmodule, nocache=False) -> ProcessResult:
    workflow = wfmodule.workflow
    target_rev = workflow.revision()

    # Do we already have what we need?
    cache = None
    if not nocache:
        cache = get_render_cache(wfmodule, target_rev)
    if cache:
        return cache

    # No, let's render from the top, shortcutting with cache whenever possible
    result = ProcessResult()

    # Start from the top, re-rendering any modules which do not have a cache at the current revision
    # Assumes not possible to have later revision cache after a module which has an earlier revision cache
    # (i.e. module stack always rendered in order)
    # If everything is rendered already, this will just return the cache
    for wfm in workflow.wf_modules.all():
        # Get module output from cache, if available and desired
        if nocache:
            cache = None
        else:
            cache = get_render_cache(wfm, target_rev)

        # if we did not find an available cache, render
        if cache:
            result = cache
        else:
            # previous revisions are dead to us now (well, maybe good for undo, but we can re-render)
            StoredObject.objects.filter(wf_module=wfm, type=StoredObject.CACHED_TABLE).delete()
            result = module_dispatch_render(wfm, result.dataframe)
            StoredObject.create_table(wfm, StoredObject.CACHED_TABLE,
                                      result.dataframe, metadata=target_rev)

        # found the module we were looking for, all done
        if wfm == wfmodule:
            break

    return result


# shortcut to execute without cache, handy for testing
def execute_nocache(wfm):
    return execute_wfmodule(wfm, nocache=True)
