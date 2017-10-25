from rest_framework import viewsets, renderers
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from django.http import HttpResponse
from server.serializers import StoredObjectSerializer
from server.models import StoredObject
from server.forms import StoredObjectForm
from server.versions import notify_client_workflow_version_changed
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
        form = StoredObjectForm(request.POST, request.FILES)
        if form.is_valid():
            new_stored_object = form.save()
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
            qs = StoredObject.objects.filter(wf_module=WfModule.objects.get(pk=wf_module)).values('uuid', 'name', 'size')
            return make_response(status=200, content=json.dumps(list(qs)))

    def delete(self, request, *args, **kwargs):
        """A DELETE request. If found, deletes a file with the corresponding
        UUID from the server's filesystem.
        """
        qquuid = kwargs.get('qquuid', '')
        if qquuid:
            instances = StoredObject.objects.filter(uuid = qquuid)
            for instance in instances:
                instance.wf_module.stored_data_version = None
                instance.wf_module.save()
                instance.delete()
            return make_response(status=204, content=json.dumps({'success': True}))
        else:
            return make_response(status=404,
                                 content=json.dumps({
                                     'success': False,
                                     'error': 'File not present'
                                 }))


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