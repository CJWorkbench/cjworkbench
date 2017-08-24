from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from django.contrib.auth import get_user_model
from server.serializers import UserSerializer

User = get_user_model()

@api_view(['GET', 'POST'])
@renderer_classes((JSONRenderer,))
def user_info(request, format=None):
    if request.method == 'GET' and request.user and request.user.is_authenticated():
        this_user = UserSerializer(request.user)
        return Response(this_user.data)
    else:
        return HttpResponseForbidden()
