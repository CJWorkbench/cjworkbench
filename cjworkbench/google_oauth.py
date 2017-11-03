from oauth2client.client import flow_from_clientsecrets
from django.http import HttpResponse, JsonResponse
from cjworkbench import settings
from django.shortcuts import redirect
from oauth2client.contrib.django_util.storage import DjangoORMStorage
from cjworkbench.models.GoogleCreds import GoogleCredentials
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote_plus, unquote_plus

flow = flow_from_clientsecrets(
    settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
    scope='https://www.googleapis.com/auth/spreadsheets.readonly https://www.googleapis.com/auth/drive.readonly',
    redirect_uri='http://localhost:8000/oauth'
)
flow.params['approval_prompt'] = 'force'

def authorize(request):
    return redirect(flow.step1_get_authorize_url())

def maybe_authorize(request, redirect_url = False):
    storage = DjangoORMStorage(GoogleCredentials, 'id', request.user, 'credential')
    credential = storage.get()
    if credential is None or credential.invalid == True:
        authorize_url = flow.step1_get_authorize_url()
        if redirect_url:
            authorize_url = add_query_param(authorize_url, 'state', redirect_url)
        return (False, authorize_url)
    else:
        return (True, credential)

def get_creds(request):
    credential = flow.step2_exchange(request.GET.get('code', False))
    storage = DjangoORMStorage(GoogleCredentials, 'id', request.user, 'credential')
    storage.put(credential)
    if request.GET.get('state', False):
        return redirect(unquote_plus(request.GET.get('state')))
    else:
        return HttpResponse(status=200)

def refresh_creds(request):
    storage = DjangoORMStorage(GoogleCredentials, 'id', request.user, 'credential')
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
