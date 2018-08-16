from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from server.importmodulefromgithub import import_module_from_github, refresh_module_from_github
import json

@api_view(['POST'])
@login_required
@renderer_classes((JSONRenderer,))
def import_from_github(request):
    try:
        returnable = import_module_from_github(request.data["url"])
        response = Response(json.dumps(returnable), content_type='application/json')
        response.status_code = status.HTTP_201_CREATED
        return response
    except ValidationError as error:
        response = HttpResponse(json.dumps({'error': error.message}),
                                content_type='application/json')
        response.status_code = 200  # should really be 400, but we want the WorkbenchAPI.js to pass error messages through
        return response
