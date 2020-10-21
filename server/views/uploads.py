from functools import wraps
import hashlib
import json
import re
from typing import Any, Dict
from uuid import UUID
from asgiref.sync import async_to_sync
from django import forms
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from cjwstate import commands
from cjwstate.models import InProgressUpload, Workflow, Step
from cjwstate.models.commands import SetStepParams
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjworkbench.models.db_object_cooperative_lock import DbObjectCooperativeLock


AuthTokenHeaderRegex = re.compile(r"\ABearer ([-a-zA-Z0-9_]+)\Z", re.IGNORECASE)


def ErrorResponse(status_code: int, error_code: str, extra_data: Dict[str, Any] = {}):
    return JsonResponse(
        {"error": {"code": error_code, **extra_data}}, status=status_code
    )


def loads_step_for_api_upload(f):
    """Provide `step` to a Django view if HTTP Authorization header matches.

    Calls `f(request, workflow_lock, step, file_param_id_name, *args, **kwargs)`

    The HTTP Authorization header must look like:

        Authorization: Bearer <STEP_FILE_UPLOAD_API_TOKEN>

    The inner function is wrapped in `workflow.cooperative_lock()`.

    Return 400 Bad Request if the Authorization header looks wrong.

    Return 404 Not Found on missing/deleted Workflow+Step.

    Return 403 Forbidden on missing/deleted Workflow+Step or on incorrect
    API token.

    A hash of the token is compared, to prevent leaking the token through a
    timing attack.
    """

    @wraps(f)
    def wrapper(
        request: HttpRequest, workflow_id: int, step_slug: str, *args, **kwargs
    ):
        auth_header = request.headers.get("Authorization", "")
        auth_header_match = AuthTokenHeaderRegex.match(auth_header)
        if not auth_header_match:
            return ErrorResponse(403, "authorization-bearer-token-not-provided")
        bearer_token = auth_header_match.group(1)

        try:
            with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow_lock:
                workflow = workflow_lock.workflow
                try:
                    step = Step.live_in_workflow(workflow).get(slug=step_slug)
                except Step.DoesNotExist:
                    return ErrorResponse(404, "step-not-found")

                try:
                    module_zipfile = MODULE_REGISTRY.latest(step.module_id_name)
                except KeyError:
                    return ErrorResponse(400, "step-module-deleted")

                try:
                    file_param_id_name = next(
                        iter(
                            pf.id_name
                            for pf in module_zipfile.get_spec().param_fields
                            if pf.type == "file"
                        )
                    )
                except StopIteration:
                    return ErrorResponse(400, "step-has-no-file-param")

                api_token = step.file_upload_api_token
                if not api_token:
                    return ErrorResponse(403, "step-has-no-api-token")

                bearer_token_hash = hashlib.sha256(
                    bearer_token.encode("utf-8")
                ).digest()
                api_token_hash = hashlib.sha256(api_token.encode("utf-8")).digest()
                if bearer_token_hash != api_token_hash or bearer_token != api_token:
                    return ErrorResponse(403, "authorization-bearer-token-invalid")

                return f(
                    request,
                    workflow_lock,
                    step,
                    file_param_id_name,
                    *args,
                    **kwargs,
                )
        except Workflow.DoesNotExist:
            return ErrorResponse(404, "workflow-not-found")

    return wrapper


@method_decorator(csrf_exempt, name="dispatch")
class UploadList(View):
    @method_decorator(loads_step_for_api_upload)
    def post(
        self,
        request: HttpRequest,
        workflow_lock: DbObjectCooperativeLock,
        step: Step,
        file_param_id_name: str,
    ):
        """Create a new InProgressUpload for the given Step.

        Authenticate request as documented in `loads_step_for_api_upload`.
        (That means respond with 400, 403 or 404 on error.)
        """
        in_progress_upload = step.in_progress_uploads.create()
        params = in_progress_upload.generate_upload_parameters()
        return JsonResponse(
            {
                **params,
                "finishUrl": request.build_absolute_uri(
                    "./uploads/" + str(in_progress_upload.id)
                ),
            }
        )


class CompleteUploadForm(forms.Form):
    filename = forms.CharField(min_length=1, max_length=100)


@method_decorator(csrf_exempt, name="dispatch")
class Upload(View):
    @method_decorator(loads_step_for_api_upload)
    def delete(
        self,
        request: HttpRequest,
        workflow_lock: DbObjectCooperativeLock,
        step: Step,
        file_param_id_name: str,
        uuid: UUID,
    ):
        """Abort an upload, or no-op if there is no upload with the given UUID.

        Authenticate request as documented in `loads_step_for_api_upload`.
        (That means respond with 400, 403 or 404 on error.)
        """
        try:
            in_progress_upload = step.in_progress_uploads.get(
                id=uuid, is_completed=False
            )
        except InProgressUpload.DoesNotExist:
            return ErrorResponse(404, "upload-not-found")
        in_progress_upload.delete_s3_data()
        in_progress_upload.is_completed = True
        in_progress_upload.save(update_fields=["is_completed"])
        return JsonResponse({})

    @method_decorator(loads_step_for_api_upload)
    def post(
        self,
        request: HttpRequest,
        workflow_lock: DbObjectCooperativeLock,
        step: Step,
        file_param_id_name: str,
        uuid: UUID,
    ):
        """Create an UploadedFile and delete the InProgressUpload.

        Authenticate request as documented in `loads_step_for_api_upload`.
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
            in_progress_upload = step.in_progress_uploads.get(
                id=uuid, is_completed=False
            )
        except InProgressUpload.DoesNotExist:
            return ErrorResponse(404, "upload-not-found")
        try:
            uploaded_file = in_progress_upload.convert_to_uploaded_file(filename)
        except FileNotFoundError:
            return ErrorResponse(409, "file-not-uploaded")

        # After the cooperative lock ends, update the Step.
        want_params = {file_param_id_name: uploaded_file.uuid}

        def create_change_parameters_command():
            workflow = workflow_lock.workflow
            # sends delta to Websockets clients and queues render.
            async_to_sync(commands.do)(
                SetStepParams,
                workflow_id=workflow.id,
                step=step,
                new_values=want_params,
            )

        workflow_lock.after_commit(create_change_parameters_command)

        return JsonResponse(
            {
                "uuid": uploaded_file.uuid,
                "name": uploaded_file.name,
                "size": uploaded_file.size,
                "createdAt": uploaded_file.created_at,
            }
        )
