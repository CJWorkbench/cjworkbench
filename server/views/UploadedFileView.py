from rest_framework import renderers, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from server.forms import UploadedFileForm
from server.modules.uploadfile import upload_to_table
from django.http import HttpResponse
from server.models import WfModule, StoredObject
import json

class UploadedFileView(APIView):
    renderer_classes = [renderers.JSONRenderer]
    parser_classes = (MultiPartParser,)
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @staticmethod
    def post(request):
        form = UploadedFileForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = form.save()
            upload_to_table(uploaded_file.wf_module, uploaded_file)
            return HttpResponse('{"success":true}', content_type="application/json", status=status.HTTP_201_CREATED)
        else:
            err = json.dumps({'success': False, 'error': '%s' % repr(form.errors)})
            return HttpResponse(err, content_type="application/json", status=status.HTTP_400_BAD_REQUEST)


    # Called by the client to get the uuid and filename of a previously uploaded file
    @staticmethod
    def get(request):
        wf_module_id = request.GET.get('wf_module', '')
        if wf_module_id == '':
            return Response({'success': False, 'error': 'Missing wf_module query parameter'},
                            status=status.HTTP_400_BAD_REQUEST)
        wf_module = WfModule.objects.get(pk=wf_module_id)

        # the UploadedFile is converted to a StoredObject when the UploadFile module first renders
        so = StoredObject.objects.filter(wf_module=wf_module, stored_at=wf_module.stored_data_version).first()
        if so and so.metadata:
            return HttpResponse(so.metadata, content_type="application/json")
        else:
            return HttpResponse('[]', content_type="application/json")  # no file has yet been uploaded

