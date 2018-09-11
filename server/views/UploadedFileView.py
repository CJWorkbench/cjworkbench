from rest_framework import renderers, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.http import HttpResponse, JsonResponse
from server.models import WfModule, StoredObject


class UploadedFileView(APIView):
    renderer_classes = [renderers.JSONRenderer]
    parser_classes = (MultiPartParser,)
    permission_classes = (IsAuthenticatedOrReadOnly,)

    # Called to get the uuid and filename of a previously uploaded file
    @staticmethod
    def get(request):
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
