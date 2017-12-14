from rest_framework import viewsets, renderers
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from django.http import HttpResponse
from server.serializers import StoredObjectSerializer
from server.models import StoredObject
from server.forms import StoredObjectForm
from server.models import ChangeDataVersionCommand

import json
import logging
import os
import os.path
import shutil

from django.conf import settings
from django.http import HttpResponse, HttpRequest
from server.models import StoredObject, WfModule

logger = logging.getLogger('django')


class StoredObjectView(APIView):
    renderer_classes = [renderers.JSONRenderer]
    parser_classes = (MultiPartParser,)

    def post(self, request, format=None):
        form = StoredObjectForm(request.POST,
                                request.FILES)
        if form.is_valid():
            new_stored_object = form.save()
            new_stored_object.type = StoredObject.UPLOADED_FILE # gross, we need a better strategy for uploaded files
            new_stored_object.save()
            ChangeDataVersionCommand.create(new_stored_object.wf_module, new_stored_object.stored_at)
            return make_response(content=json.dumps({'success': True}))
        else:
            return make_response(status=400,
                                 content=json.dumps({
                                     'success': False,
                                     'error': '%s' % repr(form.errors)
                                 }))

    def get(self, request, *args, **kwargs):
        wf_module = request.GET.get('wf_module', '')
        if wf_module == '':
            return make_response(status=400,
                                 content=json.dumps({
                                     'success': False,
                                     'error': 'Please specify the wf_module'
                                 }))
        else:
            wf_module_aux = WfModule.objects.get(pk=wf_module)
            qs = StoredObject.objects.filter(wf_module=wf_module_aux, stored_at=wf_module_aux.stored_data_version).values('uuid', 'name', 'size')
            return make_response(status=200, content=json.dumps(list(qs)))



##
# Utils
##
def make_response(status=200, content_type='text/plain', content=None):
    """ Construct a response to an upload request.
    Success is indicated by a status of 200 and { "success": true }
    contained in the content.
    Also, content-type is text/plain by default since IE9 and below chokes
    on application/json. For CORS environments and IE9 and below, the
    content-type needs to be text/html.
    """
    response = HttpResponse()
    response.status_code = status
    response['Content-Type'] = content_type
    response.content = content
    return response
