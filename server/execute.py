# Run the workflow, generating table output

from server.dispatch import module_dispatch_render
from server.websockets import ws_client_rerender_workflow
from server.modules.types import ProcessResult


# Tell client to reload (we've finished rendering)
def notify_client_workflow_version_changed(workflow):
    ws_client_rerender_workflow(workflow)


def get_render_cache(wfm, revision) -> ProcessResult:
    cached_result = wfm.get_cached_render_result()
    if cached_result and cached_result.workflow_revision == revision:
        return cached_result.result
    else:
        return None


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
            result = module_dispatch_render(wfm, result.dataframe)
            wfm.cache_render_result(target_rev, result)
            wfm.save()

        # found the module we were looking for, all done
        if wfm == wfmodule:
            break

    return result


# shortcut to execute without cache, handy for testing
def execute_nocache(wfm):
    return execute_wfmodule(wfm, nocache=True)
