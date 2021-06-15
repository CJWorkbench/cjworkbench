import json
import re
from typing import Any, Dict

from django import forms
from django.conf import settings
from django.http import HttpRequest, JsonResponse

from cjworkbench.sync import database_sync_to_async
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


@database_sync_to_async
def _raise_if_unauthorized(workflow_id: int, step_slug: str, api_token: str) -> None:
    with upload.locked_and_loaded_step(workflow_id, step_slug) as (
        _,
        step,
        __,
    ):  # raise UploadError
        upload.raise_if_api_token_is_wrong(step, api_token)  # raise UploadError


async def create_tus_upload_for_workflow_and_step(
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
        size = forms.IntegerField(
            min_value=0, max_value=settings.MAX_BYTES_FILES_PER_STEP
        )

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
        await _raise_if_unauthorized(
            workflow_id, step_slug, api_token
        )  # raise UploadError
    except upload.UploadError as err:
        return ErrorResponse(err.status_code, err.error_code, err.extra_data)

    tus_upload_url = await upload.create_tus_upload(
        workflow_id=workflow_id,
        step_slug=step_slug,
        api_token=api_token,
        filename=filename,
        size=size,
    )

    return JsonResponse({"tusUploadUrl": tus_upload_url})


create_tus_upload_for_workflow_and_step.csrf_exempt = (
    True  # Django 3.1 decorator isn't async
)
