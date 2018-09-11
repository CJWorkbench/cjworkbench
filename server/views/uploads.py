# Started with a copy/paste from:
# https://github.com/FineUploader/server-examples/blob/e678ced5f54d131cdb7ab7e9c8169a80843d3f43/python/django-fine-uploader-s3/views.py
import base64
import json
from typing import Any, Dict, Optional
from django.conf import settings
from django.http import HttpResponse, HttpRequest, JsonResponse
from minio.error import ResponseError
from server.forms import UploadedFileForm
from server.minio import minio_client, UserFilesBucket, sign
from server.modules.uploadfile import upload_to_table


def handle_completed_upload(request: HttpRequest):
    """Accept the client's POST after the file has been stored in S3."""
    form = UploadedFileForm(request.POST)

    if form.is_valid():
        uploaded_file = form.save(commit=False)  # does not write to DB
        uploaded_file.size = minio_client.stat_object(
            uploaded_file.bucket,
            uploaded_file.key
        ).size
        uploaded_file.save()
        upload_to_table(uploaded_file.wf_module, uploaded_file)
        return JsonResponse({'success': True}, status=201)
    else:
        return JsonResponse({'success': False, 'error': repr(form.errors)},
                            status=400)


def handle_s3(request):
    """ View which handles all POST and DELETE requests sent by Fine Uploader
    S3. You will need to adjust these paths/conditions based on your setup.
    """
    if request.method == "POST":
        return handle_POST(request)
    elif request.method == "DELETE":
        return handle_DELETE(request)
    else:
        return HttpResponse(status=405)


def handle_POST(request):
    """ Handle S3 uploader POST requests here. For files <=5MiB this is a simple
    request to sign the policy document. For files >5MiB this is a request
    to sign the headers to start a multipart encoded request.
    """
    if request.POST.get('success', None):
        return handle_completed_upload(request)
    else:
        request_payload = json.loads(request.body)
        headers = request_payload.get('headers', None)
        if headers:
            # The presence of the 'headers' property in the request payload
            # means this is a request to sign a REST/multipart request
            # and NOT a policy document
            response_data = sign_headers(headers)
        else:
            problem = find_policy_problem(request_payload)
            if problem:
                return JsonResponse({'invalid': True, 'problem': problem},
                                    status=400)
            response_data = sign_policy_document(request_payload)
        return JsonResponse(response_data)


def handle_DELETE(request):
    """
    Delete the user's (half-uploaded?) file.

    Filenames are random, so we assume anyone who knows the filename is the
    file's owner.
    """
    key = request.REQUEST.get('key')
    try:
        minio_client.remove_incomplete_upload(UserFilesBucket, key)
        return HttpResponse(status=204)
    except ResponseError as err:
        return JsonResponse({'error': str(err)}, status=500)


def find_policy_problem(policy_document: Dict[str, Any]) -> Optional[str]:
    """
    Audit the user's policy document to find the reason it's invalid (or None).
    """
    for condition in policy_document['conditions']:
        if isinstance(condition, list) \
           and condition[0] == 'content-length-range':
            parsed_max_size = condition[2]
            if parsed_max_size > settings.MINIO_MAX_FILE_SIZE:
                return 'Requested upload is too large'
        else:
            if condition.get('bucket', None):
                if condition['bucket'] != UserFilesBucket:
                    return f'"bucket" must be "{UserFilesBucket}"'

    return None


def sign_policy_document(policy_document):
    """
    Sign and return the policy doucument for a simple upload.

    http://aws.amazon.com/articles/1434/#signyours3postform
    """
    policy = base64.b64encode(json.dumps(policy_document).encode('utf-8'))
    signature = base64.b64encode(sign(policy))
    return {
        'policy': str(policy, 'ascii'),
        'signature': str(signature, 'ascii'),
    }


def sign_headers(headers):
    """ Sign and return the headers for a chunked upload. """
    return {
        'signature': str(base64.b64encode(sign(headers)), 'ascii'),
    }
