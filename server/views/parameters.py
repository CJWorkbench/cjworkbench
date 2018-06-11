from django.conf import settings
from django.shortcuts import redirect, render
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseBadRequest, HttpResponseServerError
from django.views.decorators.http import require_GET
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from ..models import Module, Workflow, WfModule, ParameterSpec, ParameterVal, ChangeParameterCommand
from ..serializers import ParameterValSerializer
from ..execute import execute_wfmodule
from ..dispatch import module_dispatch_event
from .. import triggerrender
import requests_oauthlib
import base64
import json
import jwt
import uuid
from typing import Union

# ---- Parameter ----

def parameter_val_or_response_for_read(
        pk: int, user: User) -> Union[HttpResponse, ParameterVal]:
    """ParameterVal the user can read, or HTTP error response."""
    try:
        param = ParameterVal.objects.get(pk=pk) # raises
    except ParameterVal.DoesNotExist:
        return HttpResponseNotFound()

    if param.user_authorized_read(user):
        return param
    else:
        return HttpResponseForbidden()


def parameter_val_or_response_for_write(
        pk: int, user: User) -> Union[HttpResponse, ParameterVal]:
    """ParameterVal the user can write, or HTTP error response."""
    try:
        param = ParameterVal.objects.get(pk=pk) # raises
    except ParameterVal.DoesNotExist:
        return HttpResponseNotFound()

    if param.user_authorized_write(user):
        return param
    else:
        return HttpResponseForbidden()


# Get or set parameter value
@api_view(['GET', 'PATCH'])
@renderer_classes((JSONRenderer,))
def parameterval_detail(request, pk, format=None):
    if request.method == 'GET':
        param = parameter_val_or_response_for_read(pk, request.user)
        if isinstance(param, HttpResponse): return param
        serializer = ParameterValSerializer(param)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        param = parameter_val_or_response_for_write(pk, request.user)
        if isinstance(param, HttpResponse): return param
        ChangeParameterCommand.create(param, request.data['value'])

        # If someone pressed enter on the primary field of a module that fetches data, e.g. like url for LoadURL
        # then also "press" the fetch button. Totes hardcoded for now, but this is probably where this feature goes
        # (can't put it in the front end b/c race conditions between setting parameter val and triggering fetch)
        if request.data.get('pressed_enter', False):
            if param.parameter_spec.id_name == 'url' and param.wf_module.module_version.module.id_name == 'loadurl':
                fake_click = {'type':'click'}
                module_dispatch_event(param.wf_module, parameter=param, event=fake_click)

        return Response(status=status.HTTP_204_NO_CONTENT)


# Handle a parameter event (like someone clicking the fetch button)
# Get or set parameter value
@api_view(['POST'])
@renderer_classes((JSONRenderer,))
def parameterval_event(request, pk, format=None):
    param = parameter_val_or_response_for_write(pk, request.user)
    if isinstance(param, HttpResponse): return param

    # change parameter value
    data = request.data
    dispatch_response = module_dispatch_event(param.wf_module, parameter=param, event=data, request=request)
    if dispatch_response:
        return dispatch_response

    return Response(status=status.HTTP_204_NO_CONTENT)


# Return a parameter val that is actually an image
@require_GET
def parameterval_png(request, pk):
    param = parameter_val_or_response_for_read(pk, request.user)
    if isinstance(param, HttpResponse): return param

    # is this actually in image? totes hardcoded for now
    if param.parameter_spec.id_name != 'chart':
        return HttpResponseBadRequest()

    # decode the base64 payload of the data URI into a png
    image_data = param.value.partition('base64,')[2]
    binary = base64.b64decode(image_data)
    return HttpResponse(binary, content_type='image/png')


OauthServices = settings.PARAMETER_OAUTH_SERVICES


def _oauth_step1_redirect(request, param: ParameterVal, id_name: str) -> HttpResponse:
    """Redirects to the specified OAuth service provider.

    Returns 404 if id_name is not configured (e.g., user asked for
    'google_credentials' but there are no Google creds and so
    PARAMETER_OAUTH_SERVICES['google_credentials'] does not exist).

    This stores the ParameterVal pk in the state, which is a URL passed to
    the remote service. When the remote service redirects to our redirect_uri
    (which does not accept parameters), it will include the state in the URL.
    """
    if id_name not in OauthServices:
        return HttpResponseNotFound(f'Oauth service for {id_name} not configured')

    service = OauthServices[id_name]

    nonce = uuid.uuid4().hex # CSRF protection -- the original intent of state
    state = f'{id_name}-{param.pk}-{nonce}'

    session = requests_oauthlib.OAuth2Session(
        client_id=service['client_id'],
        scope=service['scope'],
        redirect_uri=request.build_absolute_uri('/oauth')
    )
    url, _ = session.authorization_url(
        url=service['auth_url'],
        state=state,
        access_type='offline', approval_prompt='force'
    )

    param.value = json.dumps({
        'name': '',
        'secret': { 'state': state },
    })
    param.save()

    return redirect(url)


def _oauth_step2_handle_code(request, param: ParameterVal) -> HttpResponse:
    """Exchange `request` for an auth token and save it in param."""
    spec = param.parameter_spec
    id_name = spec.id_name
    service = OauthServices[id_name] # if we got here, id_name is valid

    session = requests_oauthlib.OAuth2Session(
        client_id=service['client_id'],
        scope=service['scope'],
        redirect_uri=request.build_absolute_uri('/oauth')
    )
    token = session.fetch_token(
        client_secret=service['client_secret'],
        token_url=service['token_url'],
        code=request.GET['code'],
        timeout=30
    )

    if not token.get('refresh_token'):
        return HttpResponseServerError(f'{id_name} did not provide a refresh_token')

    # This line may be Google-specific.
    email = jwt.decode(token['id_token'], verify=False)['email']

    with param.wf_module.workflow.cooperative_lock():
        # TODO consider ChangeParameterCommand. It might not play nice with 'secret'
        param.set_value({ 'name': email, 'secret': token })
        # Copied from ChangeParameterCommand. Clear errors in case the connect fixed things
        param.wf_module.set_ready(notify=False)

    triggerrender.notify_client_workflow_version_changed(param.wf_module.workflow)
    return HttpResponse(b"""<!DOCTYPE html>
        <html lang="en-US">
            <head>
                <title>Authorized</title>
            </head>
            <body>
                <p class="success">You have logged in, and you can close this window now.</p>
            </body>
        </html>
    """)
    


@api_view(['GET', 'DELETE'])
def parameterval_oauth_start_authorize(request, pk):
    param = parameter_val_or_response_for_write(pk, request.user)
    if isinstance(param, HttpResponse): return param

    spec = param.parameter_spec
    if spec.type != ParameterSpec.SECRET:
        return HttpResponseNotFound(f'This is a {spec.type}, not a SECRET')
    if spec.id_name not in OauthServices:
        return HttpResponseNotFound(f'We only support id_name {", ".join(OauthServices)}')

    if request.method == 'GET':
        return _oauth_step1_redirect(request, param, spec.id_name)

    elif request.method == 'DELETE':
        with param.wf_module.workflow.cooperative_lock():
            param.set_value('')
        triggerrender.notify_client_workflow_version_changed(param.wf_module.workflow)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def parameterval_oauth_finish_authorize(request) -> HttpResponse:
    """Set parameter secret to something valid.

    The external service redirects here after _we_ redirect to _it_ in
    parameterval_oauth_start_authorize(). We cannot include pk in the request,
    so we pass it to the oauth service instead and read it back here.
    """
    state = request.GET.get('state', '')
    id_name, state_pk, _ = f'{state}--'.split('-', 2)
    # we'll prove id_name is valid once we check _this_ state against the _real_ state
    # we wrote in param.value['state'].

    # is the state string remotely close to valid?
    # If not, return.
    try:
        state_pk = int(state_pk)
    except ValueError:
        return HttpResponseNotFound(f'State "{state}" did not contain an int primary key')

    # Load the specified param from the database.
    param = parameter_val_or_response_for_write(state_pk, request.user)

    # Does the param exist and belong to the user?
    # If not, return.
    if isinstance(param, HttpResponse): return param

    # Is param.value['state'] the state we wrote in the param before redirect?
    # If not, return.
    try:
        data = json.loads(param.value)
    except json.decoder.JSONDecodeError:
        # We won't describe `param.value` here, because it's a secret
        return HttpResponseNotFound(f'State "{state}" pointed to an unexpected param')
    param_state = data.get('secret', {}).get('state', '')
    if param_state != state:
        return HttpResponseNotFound(f'State "{state}" did not match the state in the database')

    # Now we know enough to handle the OAuth value.
    return _oauth_step2_handle_code(request, param)


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
    param = parameter_val_or_response_for_read(pk, request.user)
    if isinstance(param, HttpResponse): return param

    if param.wf_module.workflow.owner != request.user:
        # Let's be abundantly clear: this is a _secret_. Users give us their
        # refresh tokens under the assmption that we won't share access to all
        # their files with _anybody_.
        return HttpResponseForbidden('only the workspace owner can generate an access token')

    spec = param.parameter_spec
    if spec.type != ParameterSpec.SECRET:
        return HttpResponseForbidden(f'This is a {spec.type}, not a SECRET')
    if spec.id_name not in OauthServices:
        return HttpResponseForbidden(f'We only support id_name {", ".join(OauthServices)}')

    secret_json = param.value
    if not secret_json:
        return HttpResponseNotFound('secret not set')
    try:
        secret_data = json.loads(secret_json)
    except json.decoder.JSONDecodeError:
        return HttpResponseForbidden('non-JSON secret')
    try:
        secret = secret_data['secret']
    except KeyError:
        return HttpResponseForbidden('secret value has no secret')
    if 'refresh_token' not in secret:
        # This is possible if the user is mid-authentication
        return HttpResponseForbidden('secret has no refresh_token')

    service = OauthServices[spec.id_name]
    session = requests_oauthlib.OAuth2Session(
        client_id=service['client_id'],
        scope=service['scope'],
        redirect_uri=request.build_absolute_uri('/oauth'),
        token=secret
    )
    token = session.refresh_token(
        service['token_url'],
        client_id=service['client_id'],
        client_secret=service['client_secret']
    ) # TODO handle exceptions: revoked token, HTTP error

    # token['access_token'] is short-term (1hr). token['refresh_token'] is
    # super-private and we should never transmit it.
    return HttpResponse(token['access_token'], content_type='text/plain')
