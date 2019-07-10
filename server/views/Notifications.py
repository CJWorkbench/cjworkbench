from django.http import JsonResponse
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from server.models import WfModule


@api_view(["DELETE"])
@renderer_classes((JSONRenderer,))
def notifications_delete_by_wfmodule(request, pk, format=None):
    try:
        wf_module = WfModule.objects.get(pk=pk, is_deleted=False)
    except WfModule.DoesNotExist:
        return HttpResponseNotFound()

    if not wf_module.request_authorized_write(request):
        return HttpResponseForbidden()

    wf_module.has_unseen_notification = False
    wf_module.save(update_fields=["has_unseen_notification"])

    return JsonResponse({}, status=200)
