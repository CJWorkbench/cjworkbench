import json

from django.core.exceptions import ValidationError
from django.http import HttpResponse

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from server.importmodulefromgithub import import_module_from_github, refresh_module_from_github

@api_view(['POST'])
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
        response.status_code = 400
        return response

@api_view(['POST'])
@renderer_classes((JSONRenderer))
def refresh_from_github(request):
    try:
        refresh_module_from_github(request.data["url"])
        return Response(status=status.HTTP_201_CREATED)
    except ValidationError as error:
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
