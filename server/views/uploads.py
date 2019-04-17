# Started with a copy/paste from:
# https://github.com/FineUploader/server-examples/blob/e678ced5f54d131cdb7ab7e9c8169a80843d3f43/python/django-fine-uploader-s3/views.py
import base64
import json
from typing import Any, Dict, Optional
from asgiref.sync import async_to_sync
from django.conf import settings
from django.http import HttpResponse, HttpRequest, JsonResponse
from rest_framework.decorators import api_view
from server import rabbitmq
from server.forms import UploadedFileForm
from server import minio
from server.models import WfModule


def _delete_uploaded_file(uploaded_file):
    minio.remove(uploaded_file.bucket, uploaded_file.key)


def handle_completed_upload(request: HttpRequest):
    """Accept the client's POST after the file has been stored in S3."""
    form = UploadedFileForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False, 'error': repr(form.errors)},
                            status=400)

    uploaded_file = form.save(commit=False)  # does not write to DB

    # Auth/sanity checks delete the uploaded file when they fail. We assume the
    # user who POSTed is the user who uploaded the file (since otherwise, how
    # would they know the UUID?) -- so if we aren't going to handle the file,
    # we have no more use for it.
    try:
        wf_module = uploaded_file.wf_module
    except WfModule.DoesNotExist:
        _delete_uploaded_file(uploaded_file)
        return JsonResponse({'success': False,
                             'error': 'WfModule does not exist'},
                            status=404)

    workflow = wf_module.workflow
    if not workflow:
        # Can this happen?
        _delete_uploaded_file(uploaded_file)
        return JsonResponse({'success': False,
                             'error': 'WfModule has no Workflow'},
                            status=404)

    if not workflow.request_authorized_write(request):
        _delete_uploaded_file(uploaded_file)
        return JsonResponse({'success': False,
                             'error': 'You do not own this WfModule'},
                            status=403)

    uploaded_file.size = minio.stat(uploaded_file.bucket,
                                    uploaded_file.key).size
    uploaded_file.save()
    async_to_sync(rabbitmq.queue_handle_upload_DELETEME)(uploaded_file)
    return JsonResponse({'success': True}, status=201)


@api_view(['POST'])
def handle_s3(request):
    """ View which handles all POST requests sent by Fine Uploader
    S3. You will need to adjust these paths/conditions based on your setup.
    """
    if request.method == "POST":
        return handle_POST(request)
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
                if condition['bucket'] != minio.UserFilesBucket:
                    return f'"bucket" must be "{minio.UserFilesBucket}"'

    return None


def sign_policy_document(policy_document):
    """
    Sign and return the policy doucument for a simple upload.

    http://aws.amazon.com/articles/1434/#signyours3postform
    """
    policy = base64.b64encode(json.dumps(policy_document).encode('utf-8'))
    signature = base64.b64encode(minio.sign(policy))
    return {
        'policy': str(policy, 'ascii'),
        'signature': str(signature, 'ascii'),
    }


def sign_headers(headers):
    """ Sign and return the headers for a chunked upload. """
    header_bytes = headers.encode('utf-8')
    return {
        'signature': str(base64.b64encode(minio.sign(header_bytes)), 'ascii'),
    }
