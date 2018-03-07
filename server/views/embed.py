from django.template.response import TemplateResponse
from rest_framework.renderers import JSONRenderer
from server.models import WfModule
from server.serializers import WorkflowSerializer, WfModuleSerializer

def embed(request, wfmodule_id):
    try:
        wf_module = WfModule.objects.get(pk=wfmodule_id)
    except WfModule.DoesNotExist:
        return TemplateResponse(request, 'embed_404.html', status=404)

    if not wf_module.workflow.user_authorized_read(request.user):
        return TemplateResponse(request, 'embed_404.html', status=404)

    workflow_module_serializer = WfModuleSerializer(wf_module)
    workflow_serializer = WorkflowSerializer(wf_module.workflow)
    init_state = JSONRenderer().render({
        'workflow': workflow_serializer.data,
        'wf_module': workflow_module_serializer.data
    })
    return TemplateResponse(request, 'embed.html', {'initState': init_state})
