from django.template.response import TemplateResponse
from django.views.decorators.clickjacking import xframe_options_exempt
import json
from server.models import WfModule
from server.serializers import WorkflowSerializerLite, WfModuleSerializer


@xframe_options_exempt
def embed(request, wfmodule_id):
    try:
        wf_module = WfModule.objects.get(pk=wfmodule_id)
    except WfModule.DoesNotExist:
        wf_module = None

    if wf_module and (not wf_module.workflow.user_authorized_read(request.user) or not wf_module.module_version.html_output):
        wf_module = None

    if wf_module:
        workflow_module_serializer = WfModuleSerializer(wf_module)
        workflow_serializer = WorkflowSerializerLite(wf_module.workflow)
        init_state = {
            'workflow': workflow_serializer.data,
            'wf_module': workflow_module_serializer.data
        }
        # json.dumps barfs on datetime objects, and it's not needed here
        del (init_state['workflow'])['last_update']
    else:
        init_state = {
            'workflow': None,
            'wf_module': None
        }

    response = TemplateResponse(request, 'embed.html', {'initState': json.dumps(init_state)})
    return response
