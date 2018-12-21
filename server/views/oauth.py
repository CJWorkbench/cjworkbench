from asgiref.sync import async_to_sync
from collections import namedtuple
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, \
        HttpResponseNotFound
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from .. import oauth, websockets
from ..models import ParameterSpec, ParameterVal, WfModule, Workflow
from ..serializers import ParameterValSerializer


Scope = namedtuple('Scope', (
    'service_id',
    'state',
    'workflow_id',
    'wf_module_id',
    'param',
))


def start_authorize(request: HttpRequest, workflow_id: int, wf_module_id: int,
                    param: str):
    """
    Redirect to the external service's authentication page and write session.

    Return 404 if id_name is not configured (e.g., user asked for
    'google_credentials' but there are no Google creds and so
    PARAMETER_OAUTH_SERVICES['google_credentials'] does not exist).

    This is not done over Websockets because only an HTTP request can write a
    session cookie. (In general, that is. Let's not marry ourselves to in-DB
    sessions just to use Websockets here.
    """
    # Type conversions are guaranteed to work because we used URL regexes
    workflow_id = int(workflow_id)
    wf_module_id = int(wf_module_id)
    param = str(param)

    service = oauth.OAuthService.lookup_or_none(param)
    if not service:
        return HttpResponseNotFound(
            f'Oauth service for {param} not configured'
        )

    # Validate workflow_id, wf_module_id and param, and return
    # HttpResponseForbidden if they do not match up
    try:
        with Workflow.authorized_lookup_and_cooperative_lock(
            'owner',  # only owner can modify params
            request.user,
            request.session,
            pk=workflow_id
        ) as workflow:
            try:
                ParameterVal.objects.get(
                    wf_module__in=WfModule.live_in_workflow(workflow),
                    wf_module_id=wf_module_id,
                    parameter_spec__type=ParameterSpec.SECRET,
                    parameter_spec__id_name=param
                )
            except ParameterVal.DoesNotExist:
                return HttpResponseForbidden('Step or parameter was deleted.')
    except Workflow.DoesNotExist as err:
        # Possibilities:
        # str(err) = 'owner access denied'
        # str(err) = 'Workflow matching query does not exist'
        return HttpResponseForbidden(str(err))

    try:
        url, state = service.generate_redirect_url_and_state()
    except oauth.TokenRequestDenied:
        return TemplateResponse(request, 'oauth_token_request_denied.html',
                                status=403)

    request.session['oauth-flow'] = Scope(
        service_id=service.service_id,
        state=state,
        workflow_id=workflow_id,
        wf_module_id=wf_module_id,
        param=param
    )._asdict()

    return redirect(url)


def finish_authorize(request: HttpRequest) -> HttpResponse:
    """
    Set parameter secret to something valid.

    The external service redirects here after _we_ redirect to _it_ in
    start_authorize(). We cannot include pk in the URL (since the external
    service -- e.g., Google -- requires a fixed URL), so we store the pk in
    the session.
    """
    try:
        flow = request.session['oauth-flow']
    except KeyError:
        return HttpResponseForbidden(
            'Missing auth session. Please try connecting again.'
        )

    try:
        scope = Scope(**flow)
    except TypeError:
        # This would _normally_ be a crash-worthy exception. But there might
        # be sessions in progress as we deploy, [2018-12-21]. TODO nix this
        # `except` to keep our code clean.
        logger.exception('Malformed auth session. Data: %r', flow)
        return HttpResponseForbidden(
            'Malformed auth session. Please try connecting again.'
        )

    service = oauth.OAuthService.lookup_or_none(scope.service_id)
    if not service:
        return HttpResponseNotFound('Service not configured')

    offline_token = service.acquire_refresh_token_or_str_error(request.GET,
                                                               scope.state)
    if isinstance(offline_token, str):
        return HttpResponseForbidden(offline_token)

    username = service.extract_username_from_token(offline_token)

    try:
        with Workflow.authorized_lookup_and_cooperative_lock(
            'owner',  # only owner can modify params
            request.user,
            request.session,
            pk=scope.workflow_id
        ) as workflow:
            try:
                parameter_val = ParameterVal.objects.get(
                    wf_module__in=WfModule.live_in_workflow(workflow),
                    wf_module_id=scope.wf_module_id,
                    parameter_spec__type=ParameterSpec.SECRET,
                    parameter_spec__id_name=scope.param
                )
            except ParameterVal.DoesNotExist:
                return HttpNotFound('Step or parameter was deleted.')

            parameter_val.set_value({'name': username, 'secret': offline_token})

            vals = parameter_val.wf_module.parameter_vals \
                .prefetch_related('parameter_spec')
            delta_json = {
                'updateWfModules': {
                    str(scope.wf_module_id): {
                        'parameter_vals': (
                            ParameterValSerializer(vals, many=True).data
                        )
                    }
                }
            }
    except Workflow.DoesNotExist as err:
        # Possibilities:
        # str(err) = 'owner access denied'
        # str(err) = 'Workflow matching query does not exist'
        return HttpResponseForbidden(str(err))

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
