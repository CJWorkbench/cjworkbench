import base64
import json
import re
from typing import Any, Dict
from urllib.parse import urljoin

import httpx
from django import forms
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from cjwstate import upload

AuthTokenHeaderRegex = re.compile(r"\ABearer ([-a-zA-Z0-9_]+)\Z", re.IGNORECASE)


def ErrorResponse(status_code: int, error_code: str, extra_data: Dict[str, Any] = {}):
    return JsonResponse(
        {"error": {"code": error_code, **extra_data}}, status=status_code
    )


def get_request_bearer_token(request: HttpRequest) -> str:
    """Return Bearer token from Authorization header.

    Raise UploadError(403, "authorization-bearer-token-not-provided") if not provided.
    """
    auth_header = request.headers.get("Authorization", "")
    auth_header_match = AuthTokenHeaderRegex.match(auth_header)
    if not auth_header_match:
        raise upload.UploadError(403, "authorization-bearer-token-not-provided")
    return auth_header_match.group(1)


@csrf_exempt
def create_tus_upload_for_workflow_and_step(
    request: HttpRequest, workflow_id: int, step_slug: str
) -> JsonResponse:
    """Request that tusd create a file for this workflow and step.

    In the cloud, we block tusd from serving POST requests. Only frontend may
    create uploads; and then it's up to the client (or cloud object lifecycle
    policy) to delete them.

    We are Step 1 of the following process:

    1. Client calls Frontend API method, "create upload" (with metadata)
        1.1 Frontend calls tusd POST to create the file (with more metadata)
        1.2 Frontend returns tusd URL the client _can_ access
    2. Client uploads to tusd
        2.1 tusd calls "pre-finish" hook on Frontend
        2.2 Frontend moves file to its final location

    The HTTP request headers must include:

        Authorization: Bearer <STEP_FILE_UPLOAD_API_TOKEN>
        Content-Type: application/json

    The HTTP request body must be JSON like:

        {
            "filename": "my-filename.csv",
            "size": 1234
        }

    The (non-error) HTTP response will be JSON like:

        {
            "tusUploadUrl": "https://uploads.example.com/123dsf1234"
        }

    Clients may use the TUS protocol to upload to that url.

    Return 400 Bad Request if the Authorization header looks wrong.

    Return 404 Not Found on missing/deleted Workflow+Step.

    Return 403 Forbidden on missing/deleted Workflow+Step or on incorrect
    API token.

    Return 400 Bad Request if the content is not JSON with exactly "filename"
    (String) and "size" (integer Number) values.
    """
    # TODO ban invalid filenames
    # TODO ban invalid sizes
    # TODO require application/json body

    # declare form inline, so unit tests can override settings
    class CreateUploadForm(forms.Form):
        filename = forms.CharField(min_length=1, max_length=100)
        size = forms.IntegerField(min_value=0, max_value=settings.MINIO_MAX_FILE_SIZE)

    try:
        body_json = json.loads(request.body)  # assume UTF-8
    except UnicodeDecodeError:
        return ErrorResponse(400, "body-not-utf8")
    except json.JSONDecodeError:
        return ErrorResponse(400, "body-not-json")

    form = CreateUploadForm(body_json)
    if form.errors:
        return ErrorResponse(
            400, "body-has-errors", {"errors": form.errors.get_json_data()}
        )
    filename = form.cleaned_data["filename"]
    size = form.cleaned_data["size"]

    try:
        api_token = get_request_bearer_token(request)  # raise UploadError
        with upload.locked_and_loaded_step(workflow_id, step_slug) as (
            workflow_lock,
            step,
            _,
        ):  # raise UploadError
            upload.raise_if_api_token_is_wrong(step, api_token)  # raise UploadError
            upload_metadata_header = b"filename %s,workflowId %s,stepSlug %s,apiToken %s" % (
                base64.b64encode(filename.encode("utf-8")),
                base64.b64encode(str(workflow_id).encode("utf-8")),
                base64.b64encode(step_slug.encode("utf-8")),
                # We include apiToken: after a user resets apiToken,
                # all prior uploads must break. Rely on storage-layer
                # encryption to encrypt the API token, and on object
                # lifecycle to delete the API token reasonably swiftly.
                # Assume that users can't guess the response location:
                # therefore, the only users who can access the location
                # (and thus read the API token from a HEAD response
                # header) are the ones who already have the API token.
                base64.b64encode(api_token.encode("utf-8")),
            )
            response = httpx.post(
                settings.TUS_CREATE_UPLOAD_URL,
                headers={
                    "Tus-Resumable": "1.0.0",
                    "Upload-Length": str(size).encode("utf-8"),
                    "Upload-Metadata": upload_metadata_header,
                },
            )
    except upload.UploadError as err:
        return ErrorResponse(err.status_code, err.error_code, err.extra_data)

    if response.status_code != 201:
        raise RuntimeError("Unexpected TUS response: %r" % response)

    original_tus_upload_url = urljoin(
        settings.TUS_CREATE_UPLOAD_URL, response.headers["location"]
    )

    tus_upload_url = original_tus_upload_url.replace(
        settings.TUS_CREATE_UPLOAD_URL, settings.TUS_EXTERNAL_URL_PREFIX_OVERRIDE
    )

    return JsonResponse({"tusUploadUrl": tus_upload_url})
