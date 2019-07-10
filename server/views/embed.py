from django.template.response import TemplateResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from server.models import WfModule
from server.serializers import WorkflowSerializerLite, WfModuleSerializer


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
        workflow_module_serializer = WfModuleSerializer(wf_module)
        workflow_serializer = WorkflowSerializerLite(
            wf_module.workflow, context={"request": request}
        )
        init_state = {
            "workflow": workflow_serializer.data,
            "wf_module": workflow_module_serializer.data,
        }
    else:
        init_state = {"workflow": None, "wf_module": None}

    response = TemplateResponse(request, "embed.html", {"initState": init_state})
    return response
