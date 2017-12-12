from oauth2client.client import flow_from_clientsecrets
from django.http import HttpResponse, JsonResponse
from cjworkbench import settings
from django.shortcuts import redirect
from oauth2client.contrib.django_util.storage import DjangoORMStorage
from cjworkbench.models.GoogleCreds import GoogleCredentials
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote_plus, unquote_plus
import jsonpickle

def create_and_store_flow(request):
    flow = flow_from_clientsecrets(
        settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
        scope='https://www.googleapis.com/auth/drive.readonly',
        redirect_uri=request.build_absolute_uri('/oauth')
    )
    flow.params['approval_prompt'] = 'force'
    request.session['flow'] = jsonpickle.encode(flow)
    return flow

def authorize(request):
    flow = create_and_store_flow(request)
    return redirect(flow.step1_get_authorize_url())

def maybe_authorize(request, redirect_url = False):
    storage = DjangoORMStorage(GoogleCredentials, 'id', request.user, 'credential')
    credential = storage.get()
    if credential is None or credential.invalid == True:
        authorize_url = create_and_store_flow(request)
        if redirect_url:
            authorize_url = add_query_param(authorize_url, 'state', redirect_url)
        return (False, authorize_url)
    else:
        return (True, credential)

def get_creds(request):
    flow = jsonpickle.decode(request.session['flow'])
    credential = flow.step2_exchange(request.GET.get('code', False))
    storage = DjangoORMStorage(GoogleCredentials, 'id', request.user, 'credential')
    storage.put(credential)
    if request.GET.get('state', False):
        return redirect(unquote_plus(request.GET.get('state')))
    else:
        return HttpResponse(status=200)


def add_query_param(url, param_name, param_value):
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qsl(query_string)

    query_params.append((param_name, quote_plus(param_value)))
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))
