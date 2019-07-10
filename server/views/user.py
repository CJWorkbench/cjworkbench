from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view, renderer_classes
from server.serializers import UserSerializer
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer


# Return current user
@api_view(["GET"])
@renderer_classes((JSONRenderer,))
def current_user(request, format=None):
    user_data = UserSerializer(request.user)
    return Response(user_data.data)
