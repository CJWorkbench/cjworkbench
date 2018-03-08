from django.template.response import TemplateResponse
from rest_framework.renderers import JSONRenderer
from server.models import WfModule
from server.serializers import WorkflowSerializerLite, WfModuleSerializer
from django.views.decorators.clickjacking import xframe_options_exempt


@xframe_options_exempt
def embed(request, wfmodule_id):
    try:
        wf_module = WfModule.objects.get(pk=wfmodule_id)
    except WfModule.DoesNotExist:
        wf_module = None

    if not wf_module.workflow.user_authorized_read(request.user) or not wf_module.module_version.html_output:
        wf_module = None

    if wf_module:
        workflow_module_serializer = WfModuleSerializer(wf_module)
        workflow_serializer = WorkflowSerializerLite(wf_module.workflow)
        init_state = JSONRenderer().render({
            'workflow': workflow_serializer.data,
            'wf_module': workflow_module_serializer.data
        })
    else:
        init_state = JSONRenderer().render({
            'workflow': None,
            'wf_module': None
        })

    response = TemplateResponse(request, 'embed.html', {'initState': init_state})
    return response
