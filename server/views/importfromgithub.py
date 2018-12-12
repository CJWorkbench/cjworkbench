from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from server.importmodulefromgithub import import_module_from_github, refresh_module_from_github
import json

@api_view(['POST'])
@login_required
def import_from_github(request):
    try:
        module = import_module_from_github(request.data["url"])
        return JsonResponse(module, status=status.HTTP_201_CREATED)
    except ValidationError as err:
        # Respond with 200 OK so the client side can read the error message.
        # TODO make the client smarter
        return JsonResponse({'error': str(err)},
                            status=status.HTTP_200_OK)
