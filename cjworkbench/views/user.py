from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view, renderer_classes
from server.serializers import UserSerializer
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from .. import google_oauth


# Return current user
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def current_user(request, format=None):
    user_data = UserSerializer(request.user)
    return Response(user_data.data)


@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def current_user_google_client_access_token(request, format=None):
    credential = google_oauth.user_to_existing_oauth2_credential(request.user)
    if not credential: return Response({})

    access_token = credential.get_access_token()

    return Response({
        'access_token': access_token.access_token,
        'expires_in': access_token.expires_in,
    })


@api_view(['DELETE'])
@renderer_classes((JSONRenderer,))
def delete_google_creds(request, format=None):
    try:
        credential = request.user.google_credentials
        credential.delete()
    except ObjectDoesNotExist:
        pass

    user_data = UserSerializer(request.user)
    return Response(user_data.data)
