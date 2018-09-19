from rest_framework.decorators import api_view
from rest_framework import status
from django.http import HttpResponse, JsonResponse
from server.models import WfModule, StoredObject


@api_view(['GET'])
def get_uploadedfile(request):
    wf_module_id = request.GET.get('wf_module', '')
    if wf_module_id == '':
        return JsonResponse({'success': False,
                             'error': 'Missing wf_module query parameter'},
                            status=status.HTTP_400_BAD_REQUEST)
    wf_module = WfModule.objects.get(pk=wf_module_id)

    # the UploadedFile is converted to a StoredObject when the UploadFile
    # module first renders
    so = StoredObject.objects.filter(
        wf_module=wf_module,
        stored_at=wf_module.stored_data_version
    ).first()
    if so and so.metadata:
        return HttpResponse(so.metadata, content_type="application/json")
    else:
        # no file has yet been uploaded
        return JsonResponse([])
