import pandas as pd
from server.dispatch import module_dispatch_render
from server.websockets import ws_client_rerender_workflow
from server.modules.types import ProcessResult
from server.models import WfModule


# Tell client to reload (we've finished rendering)
def notify_client_workflow_version_changed(workflow):
    ws_client_rerender_workflow(workflow)


def get_render_cache(wfm, revision) -> ProcessResult:
    cached_result = wfm.get_cached_render_result()
    if cached_result and cached_result.workflow_revision == revision:
        return cached_result.result
    else:
        return None


def _execute_one_wfmodule(wf_module: WfModule, input_table: pd.DataFrame, *,
                          use_cache: bool,
                          workflow_revision: int) -> ProcessResult:
    if use_cache:
        cached_result = get_render_cache(wf_module, workflow_revision)
        if cached_result:
            return cached_result

    result = module_dispatch_render(wf_module, input_table)
    if use_cache:
        wf_module.cache_render_result(workflow_revision, result)
        wf_module.save()

    return result


# Return the output of a particular module. Gets from cache if possible
def execute_wfmodule(wfmodule, nocache=False) -> ProcessResult:
    """
    Process all WfModules until the given one; return its result.

    By default, this will both read and write each WfModule's cached render
    result. Pass nocache=True to avoid modifying the cache.

    You must call this within a workflow.cooperative_lock().
    """
    workflow = wfmodule.workflow
    target_rev = workflow.revision()

    # Do we already have what we need? If so, return quickly.
    if not nocache:
        cached_result = get_render_cache(wfmodule, target_rev)
        if cached_result:
            return cached_result

    # Render from the top, shortcutting with cache whenever possible
    result = ProcessResult()

    for wfm in workflow.wf_modules.all():
        result = _execute_one_wfmodule(wfm, result.dataframe,
                                       use_cache=not nocache,
                                       workflow_revision=target_rev)

        # found the module we were looking for, all done
        if wfm == wfmodule:
            break

    return result


# shortcut to execute without cache, handy for testing
def execute_nocache(wfm):
    return execute_wfmodule(wfm, nocache=True)
