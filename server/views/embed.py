from django.template.response import TemplateResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from cjwstate.models import WfModule
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

    if wf_module and (
        not wf_module.workflow
        or not wf_module.workflow.request_authorized_read(request)
        or not wf_module.module_version
        or not wf_module.module_version.html_output
    ):
        wf_module = None

    if wf_module:
        ctx = JsonizeContext(request.user, request.session, request.locale_id)
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
