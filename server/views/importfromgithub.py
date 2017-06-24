from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from server.importmodulefromgithub import import_module_from_github, refresh_module_from_github
from server.serializers import WorkflowSerializerLite

@api_view(['POST'])
@renderer_classes((JSONRenderer,))
def import_from_github(request):
    serializer = WorkflowSerializerLite(request, many=True)
    try:
        import_module_from_github(request.data["url"])
        return Response(status=status.HTTP_201_CREATED)
    except ValidationError as error:
        return Response(error, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@renderer_classes((JSONRenderer))
def refresh_from_github(request):
    serializer = WorkflowSerializerLite(request, many=True)
    try:
        refresh_module_from_github(request.data["url"])
        return Response(status=status.HTTP_201_CREATED)
    except ValidationError as error:
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
