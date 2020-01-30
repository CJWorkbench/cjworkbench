from django.template.response import TemplateResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from cjwstate.models import WfModule
from cjwstate.models.module_registry import MODULE_REGISTRY
from server.serializers import (
    JsonizeContext,
    jsonize_clientside_workflow,
    jsonize_clientside_step,
)


@xframe_options_exempt
def embed(request, wfmodule_id):
    try:
        wf_module = WfModule.objects.get(pk=wfmodule_id, is_deleted=False)
    except WfModule.DoesNotExist:
        wf_module = None

    if wf_module:
        if not wf_module.workflow:
            wf_module = None
        elif not wf_module.workflow.request_authorized_read(request):
            wf_module = None
        else:
            try:
                module_zipfile = MODULE_REGISTRY.latest(wf_module.module_id_name)
                if not module_zipfile.get_spec().html_output:
                    wf_module = None
            except KeyError:
                wf_module = None

    if wf_module:
        ctx = JsonizeContext(
            request.user,
            request.session,
            request.locale_id,
            {module_zipfile.module_id: module_zipfile},
        )
        init_state = {
            "workflow": jsonize_clientside_workflow(
                wf_module.workflow.to_clientside(include_tab_slugs=False),
                ctx,
                is_init=True,
            ),
            "wf_module": jsonize_clientside_step(wf_module.to_clientside(), ctx),
        }
    else:
        init_state = {"workflow": None, "wf_module": None}

    return TemplateResponse(request, "embed.html", {"initState": init_state})
