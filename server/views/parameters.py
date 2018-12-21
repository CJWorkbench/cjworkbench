import json
from asgiref.sync import async_to_sync
from typing import Union
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, \
        HttpResponseNotFound
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .. import oauth, websockets
from ..models import ParameterSpec, ParameterVal
from ..serializers import ParameterValSerializer


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

    try:
        url, state = service.generate_redirect_url_and_state()
    except oauth.TokenRequestDenied:
        return TemplateResponse(request, 'oauth_token_request_denied.html',
                                status=403)

    request.session['oauth-flow'] = {
        'state': state,
        'service-id': service.service_id,
        'param-pk': param.pk,
    }

    return redirect(url)


@api_view(['GET'])
def parameterval_oauth_start_authorize(request, pk):
    param = parameter_val_or_response_for_write(pk, request)
    if isinstance(param, HttpResponse):
        return param

    spec = param.parameter_spec
    if spec.type != ParameterSpec.SECRET:
        return HttpResponseNotFound(f'This is a {spec.type}, not a SECRET')

    return _oauth_start_authorize(request, param, spec.id_name)


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

    wf_module = param.wf_module
    workflow = wf_module.workflow
    with workflow.cooperative_lock():
        # TODO consider ChangeParametersCommand. It might not play nice with
        # 'secret'
        param.set_value({'name': username, 'secret': offline_token})
        # Copied from ChangeParametersCommand. Clear errors in case the connect
        # fixed things
        param.wf_module.set_ready()

        vals = wf_module.parameter_vals.prefetch_related('parameter_spec')
        delta_json = {
            'updateWfModules': {
                str(wf_module.id): {
                    'parameter_vals': ParameterValSerializer(vals,
                                                             many=True).data
                }
            }
        }

    async_to_sync(websockets.ws_client_send_delta_async)(workflow.id,
                                                         delta_json)
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
