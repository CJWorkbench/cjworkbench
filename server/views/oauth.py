import requests_oauthlib
from oauth2client.client import flow_from_clientsecrets, OAuth2Credentials
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import redirect
from cjworkbench.models.GoogleCreds import GoogleCredentials
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote_plus, unquote_plus
from typing import Optional
import jsonpickle

def create_and_store_flow(request, storage):
    flow = flow_from_clientsecrets(
        settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
        scope = 'https://www.googleapis.com/auth/drive.readonly',
        redirect_uri = request.build_absolute_uri('/oauth')
    )
    flow.params['approval_prompt'] = 'force'
    flow.params['state'] = storage.pk
    storage.flow = flow
    storage.save()
    return flow

def authorize(request):
    storage, created = GoogleCredentials.objects.get_or_create(user=request.user)
    flow = create_and_store_flow(request, storage)
    return redirect(flow.step1_get_authorize_url())

def user_to_existing_oauth2_credential(user: User) -> Optional[OAuth2Credentials]:
    """Retrieve user's credential, or None if user has not logged in."""
    try:
        google_credentials = user.google_credentials
    except ObjectDoesNotExist:
        return None

    credential = google_credentials.credential
    if credential is None or credential.invalid: return None

    return credential


def maybe_authorize(request, user = False, redirect_url = False):
    if user:
        credential_user = user
    else:
        credential_user = request.user
    storage, created = GoogleCredentials.objects.get_or_create(user=credential_user)
    credential = storage.credential
    if credential is None or credential.invalid == True:
        flow = create_and_store_flow(request, storage)
        authorize_url = flow.step1_get_authorize_url()
        #removed until we come up with a better way of dealing with state
        #if redirect_url:
            #authorize_url = add_query_param(authorize_url, 'state', redirect_url)
        return (False, authorize_url)
    else:
        return (True, credential)

def get_creds(request):
    storage = GoogleCredentials.objects.get(pk=request.GET.get('state'))
    flow = storage.flow
    credential = flow.step2_exchange(request.GET.get('code', False))
    storage.credential = credential
    storage.save()

    #don't do this, all we do right now is close the window anyway
    #if request.GET.get('state', False):
        #return redirect(unquote_plus(request.GET.get('state')))
    #else:

    return HttpResponse(status=200)

#not used for now
def add_query_param(url, param_name, param_value):
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qsl(query_string)

    query_params.append((param_name, quote_plus(param_value)))
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))

