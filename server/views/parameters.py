import json
from asgiref.sync import async_to_sync
from typing import Union
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, \
        HttpResponseNotFound
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from ..models import ParameterSpec, ParameterVal, ChangeParameterCommand
from ..serializers import ParameterValSerializer
from ..dispatch import module_dispatch_event
from .. import triggerrender
from .. import oauth


def parameter_val_or_response_for_read(
        pk: int, request: HttpRequest) -> Union[HttpResponse, ParameterVal]:
    """ParameterVal the user can read, or HTTP error response."""
    try:
        param = ParameterVal.objects.get(pk=pk)  # raises
    except ParameterVal.DoesNotExist:
        return HttpResponseNotFound('Param not found')

    if param.request_authorized_read(request):
        return param
    else:
        return HttpResponseForbidden('Not allowed to read param')


def parameter_val_or_response_for_write(
        pk: int, request: HttpRequest) -> Union[HttpResponse, ParameterVal]:
    """ParameterVal the user can write, or HTTP error response."""
    try:
        param = ParameterVal.objects.get(pk=pk)  # raises
    except ParameterVal.DoesNotExist:
        return HttpResponseNotFound('Param not found')

    if param.request_authorized_write(request):
        return param
    else:
        return HttpResponseForbidden('Not allowed to write param')


# Get or set parameter value
@api_view(['GET', 'PATCH'])
@renderer_classes((JSONRenderer,))
def parameterval_detail(request, pk, format=None):
    if request.method == 'GET':
        param = parameter_val_or_response_for_read(pk, request)
        if isinstance(param, HttpResponse):
            return param
        serializer = ParameterValSerializer(param)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        param = parameter_val_or_response_for_write(pk, request)
        if isinstance(param, HttpResponse):
            return param
        async_to_sync(ChangeParameterCommand.create)(param,
                                                     request.data['value'])
        return Response(status=status.HTTP_204_NO_CONTENT)


# Handle a parameter event (like someone clicking the fetch button)
# Get or set parameter value
@api_view(['POST'])
@renderer_classes((JSONRenderer,))
def parameterval_event(request, pk, format=None):
    param = parameter_val_or_response_for_write(pk, request)
    if isinstance(param, HttpResponse):
        return param
    data = request.data

    dispatch_response = async_to_sync(module_dispatch_event)(
        param.wf_module,
        parameter=param,
        event=data,
        request=request
    )
    if dispatch_response:
        return dispatch_response

    return Response(status=status.HTTP_204_NO_CONTENT)


def _oauth_start_authorize(request, param: ParameterVal,
                           id_name: str) -> HttpResponse:
    """Redirects to the specified OAuth service provider.

    Returns 404 if id_name is not configured (e.g., user asked for
    'google_credentials' but there are no Google creds and so
    PARAMETER_OAUTH_SERVICES['google_credentials'] does not exist).

    This stores the ParameterVal pk in the state, which is a URL passed to
    the remote service. When the remote service redirects to our redirect_uri
    (which does not accept parameters), it will include the state in the URL.
    """
    service = oauth.OAuthService.lookup_or_none(id_name)
    if not service:
        return HttpResponseNotFound(
            f'Oauth service for {id_name} not configured'
        )

    url, state = service.generate_redirect_url_and_state()

    request.session['oauth-flow'] = {
        'state': state,
        'service-id': service.service_id,
        'param-pk': param.pk,
    }

    return redirect(url)


@api_view(['GET', 'DELETE'])
def parameterval_oauth_start_authorize(request, pk):
    param = parameter_val_or_response_for_write(pk, request)
    if isinstance(param, HttpResponse):
        return param

    spec = param.parameter_spec
    if spec.type != ParameterSpec.SECRET:
        return HttpResponseNotFound(f'This is a {spec.type}, not a SECRET')

    if request.method == 'GET':
        return _oauth_start_authorize(request, param, spec.id_name)

    elif request.method == 'DELETE':
        with param.wf_module.workflow.cooperative_lock():
            param.set_value('')
        async_to_sync(triggerrender.notify_client_workflow_version_changed)(
            param.wf_module.workflow
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def parameterval_oauth_finish_authorize(request) -> HttpResponse:
    """Set parameter secret to something valid.

    The external service redirects here after _we_ redirect to _it_ in
    parameterval_oauth_start_authorize(). We cannot include pk in that request
    (since our client id is married to our redirect_url), so we pass pk in
    session['oauth-flow'].
    """
    try:
        flow = request.session['oauth-flow']
    except KeyError:
        return HttpResponseForbidden('Did not expect auth response.')

    param = parameter_val_or_response_for_write(flow['param-pk'], request)
    if isinstance(param, HttpResponse):
        return param

    service = oauth.OAuthService.lookup_or_none(flow['service-id'])
    if not service:
        return HttpResponseNotFound('Service not configured')

    offline_token = service.acquire_refresh_token_or_str_error(request.GET,
                                                               flow['state'])
    if isinstance(offline_token, str):
        return HttpResponseForbidden(offline_token)

    username = service.extract_username_from_token(offline_token)

    with param.wf_module.workflow.cooperative_lock():
        # TODO consider ChangeParameterCommand. It might not play nice with
        # 'secret'
        param.set_value({'name': username, 'secret': offline_token})
        # Copied from ChangeParameterCommand. Clear errors in case the connect
        # fixed things
        param.wf_module.set_ready()

    async_to_sync(triggerrender.notify_client_workflow_version_changed)(
        param.wf_module.workflow
    )
    return HttpResponse(b"""<!DOCTYPE html>
        <html lang="en-US">
            <head>
                <title>Authorized</title>
            </head>
            <body>
                <p class="success">
                    You have logged in. You can close this window now.
                </p>
            </body>
        </html>
    """)


@api_view(['POST'])
def parameterval_oauth_generate_access_token(request, pk) -> HttpResponse:
    """Return a temporary access_token the client can use.

    Only the owner can generate an access token: we must keep the secret away
    from prying eyes. This access token lets the client read all the owner's
    documents on GDrive.

    The response is always text/plain. Status codes:

    200 OK -- a token
    404 Not Found -- param not found, or param has no secret
    403 Forbidden -- user not allowed to generate token

    We expect the caller to silently accept 404 Not Found but log other errors.
    """
    param = parameter_val_or_response_for_read(pk, request)
    if isinstance(param, HttpResponse):
        return param

    workflow = param.wf_module.workflow
    # Let's be abundantly clear: this is a _secret_. Users give us their
    # refresh tokens under the assmption that we won't share access to all
    # their files with _anybody_.
    #
    # We aren't checking if writes are allowed. We're checking the user's
    # identity.
    #
    # See Workflow.request_authorized_write(), which is _currently_ the same
    # but may not stay that way.
    is_owner = False
    if request.user and request.user == workflow.owner:
        is_owner = True
    if workflow.anonymous_owner_session_key and request.session.session_key:
        if workflow.anonymous_owner_session_key == request.session.session_key:
            is_owner = True
    if not is_owner:
        return HttpResponseForbidden(
            'Only the workspace owner can generate an access token'
        )

    spec = param.parameter_spec
    if spec.type != ParameterSpec.SECRET:
        return HttpResponseForbidden(f'This is a {spec.type}, not a SECRET')

    service = oauth.OAuthService.lookup_or_none(spec.id_name)
    if not service:
        allowed_services = settings.PARAMETER_OAUTH_SERVICES.keys()
        return HttpResponseForbidden(
            f'We only support id_name {", ".join(allowed_services)}'
        )

    secret_json = param.value
    if not secret_json:
        return HttpResponseNotFound('secret not set')
    try:
        secret_data = json.loads(secret_json)
    except json.decoder.JSONDecodeError:
        return HttpResponseForbidden('non-JSON secret')
    try:
        offline_token = secret_data['secret']
    except KeyError:
        return HttpResponseForbidden('secret value has no secret')

    token = service.generate_access_token_or_str_error(offline_token)
    if isinstance(token, str):
        return HttpResponseForbidden(token)

    # token['access_token'] is short-term (1hr). token['refresh_token'] is
    # super-private and we should never transmit it.
    return HttpResponse(token['access_token'], content_type='text/plain')
