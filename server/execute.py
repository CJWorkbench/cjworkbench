from server.modules.types import ProcessResult
from server import dispatch
from server.models import WfModule


def get_render_cache(wf_module: WfModule) -> ProcessResult:
    revision = wf_module.last_relevant_delta_id or 0
    cached_result = wf_module.get_cached_render_result()
    if cached_result and cached_result.delta_id == revision:
        return cached_result.result
    else:
        return None


# Return the output of a particular module. Gets from cache if possible
def execute_wfmodule(wf_module: WfModule) -> ProcessResult:
    """
    Process all WfModules until the given one; return its result.

    By default, this will both read and write each WfModule's cached render
    result. Pass nocache=True to avoid modifying the cache.

    You must call this within a workflow.cooperative_lock().
    """
    # Do we already have what we need? If so, return quickly.
    cached_result = get_render_cache(wf_module)
    if cached_result:
        return cached_result

    # Recurse -- ensuring the smallest possible number of renders
    input_wf_module = wf_module.previous_in_stack()
    if input_wf_module:
        input_result = execute_wfmodule(input_wf_module)
    else:
        input_result = ProcessResult()

    result = dispatch.module_dispatch_render(wf_module, input_result.dataframe)
    wf_module.cache_render_result(wf_module.last_relevant_delta_id, result)
    wf_module.save()
    return result
