from functools import wraps
import hashlib
import json
import re
import time
from typing import Any, Dict
from uuid import UUID
from django import forms
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from server.models import InProgressUpload, Workflow, WfModule


AuthTokenHeaderRegex = re.compile(r"\ABearer ([-a-zA-Z0-9_]+)\Z", re.IGNORECASE)


def ErrorResponse(status_code: int, error_code: str, extra_data: Dict[str, Any] = {}):
    return JsonResponse(
        {"error": {"code": error_code, **extra_data}}, status=status_code
    )


def loads_wf_module_for_api_upload(f):
    """
    Provide `wf_module` to a Django view if HTTP Authorization header matches.

    The HTTP Authorization header must look like:

        Authorization: Bearer <WF_MODULE_FILE_UPLOAD_API_TOKEN>

    The inner function is wrapped in `workflow.cooperative_lock()`.

    Return 400 Bad Request if the Authorization header looks wrong.

    Return 404 Not Found on missing/deleted Workflow+WfModule.

    Return 403 Forbidden on missing/deleted Workflow+WfModule or on incorrect
    API token.

    A hash of the token is compared, to prevent leaking the token through a
    timing attack.
    """

    @wraps(f)
    def wrapper(
        request: HttpRequest, workflow_id: int, wf_module_slug: str, *args, **kwargs
    ):
        auth_header = request.headers.get("Authorization", "")
        auth_header_match = AuthTokenHeaderRegex.match(auth_header)
        if not auth_header_match:
            return ErrorResponse(403, "authorization-bearer-token-not-provided")
        bearer_token = auth_header_match.group(1)

        try:
            with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow:
                try:
                    wf_module = WfModule.live_in_workflow(workflow).get(
                        slug=wf_module_slug
                    )
                except WfModule.DoesNotExist:
                    return ErrorResponse(404, "step-not-found")

                api_token = wf_module.file_upload_api_token
                if not api_token:
                    return ErrorResponse(403, "step-has-no-api-token")

                bearer_token_hash = hashlib.sha256(
                    bearer_token.encode("utf-8")
                ).digest()
                api_token_hash = hashlib.sha256(api_token.encode("utf-8")).digest()
                if bearer_token_hash != api_token_hash or bearer_token != api_token:
                    return ErrorResponse(403, "authorization-bearer-token-invalid")

                return f(request, wf_module, *args, **kwargs)
        except Workflow.DoesNotExist:
            return ErrorResponse(404, "workflow-not-found")

    return wrapper


class UploadList(View):
    @method_decorator(loads_wf_module_for_api_upload)
    def post(self, request: HttpRequest, wf_module: WfModule):
        """
        Create a new InProgressUpload for the given WfModule.

        Authenticate request as documented in `loads_wf_module_for_api_upload`.
        (That means respond with 400, 403 or 404 on error.)
        """
        in_progress_upload = wf_module.in_progress_uploads.create()
        params = in_progress_upload.generate_upload_parameters()

        # Workaround for https://github.com/minio/minio/issues/7991
        #
        # A race in minio means these credentials might not be valid yet.
        # Workaround: give the minio+etcd machines an extra 2s to synchronize.
        time.sleep(2)  # DELETEME when minio is fixed.
        return JsonResponse(params)


class CompleteUploadForm(forms.Form):
    filename = forms.CharField(min_length=1, max_length=100)


class Upload(View):
    @method_decorator(loads_wf_module_for_api_upload)
    def delete(self, request: HttpRequest, wf_module: WfModule, uuid: UUID):
        """
        Abort an upload, or no-op if there is no upload with the given UUID.

        Authenticate request as documented in `loads_wf_module_for_api_upload`.
        (That means respond with 400, 403 or 404 on error.)
        """
        try:
            in_progress_upload = wf_module.in_progress_uploads.get(
                id=uuid, is_completed=False
            )
        except InProgressUpload.DoesNotExist:
            return ErrorResponse(404, "upload-not-found")
        in_progress_upload.delete_s3_data()
        in_progress_upload.is_completed = True
        in_progress_upload.save(update_fields=["is_completed"])
        return JsonResponse({})

    @method_decorator(loads_wf_module_for_api_upload)
    def post(self, request: HttpRequest, wf_module: WfModule, uuid: UUID):
        """
        Create an UploadedFile and delete the InProgressUpload.

        Authenticate request as documented in `loads_wf_module_for_api_upload`.
        (That means respond with 400, 403 or 404 on error.)

        Return 400 Bad Request unless the JSON body looks like:

            {"filename": "a-filename.csv"}
        """
        try:
            body_json = json.loads(request.body)  # assume UTF-8
        except UnicodeDecodeError:
            return ErrorResponse(400, "body-not-utf8")
        except json.JSONDecodeError:
            return ErrorResponse(400, "body-not-json")
        form = CompleteUploadForm(body_json)
        if form.errors:
            return ErrorResponse(
                400, "body-has-errors", {"errors": form.errors.get_json_data()}
            )
        filename = form.cleaned_data["filename"]

        try:
            in_progress_upload = wf_module.in_progress_uploads.get(
                id=uuid, is_completed=False
            )
        except InProgressUpload.DoesNotExist:
            return ErrorResponse(404, "upload-not-found")
        try:
            uploaded_file = in_progress_upload.convert_to_uploaded_file(filename)
        except FileNotFoundError:
            return ErrorResponse(409, "file-not-uploaded")
        return JsonResponse(
            {
                "uuid": uploaded_file.uuid,
                "name": uploaded_file.name,
                "size": uploaded_file.size,
                "createdAt": uploaded_file.created_at,
            }
        )
