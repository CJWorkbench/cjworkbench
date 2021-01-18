import json
import uuid
from pathlib import PurePath
from typing import Any, Dict

from django.http import HttpRequest, JsonResponse

from cjworkbench.sync import database_sync_to_async
from cjwstate import commands, s3, upload
from cjwstate.models.commands.set_step_params import SetStepParams
from cjwstate.models.uploaded_file import delete_old_files_to_enforce_storage_limits


@database_sync_to_async
def _finish_upload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an UploadedFile by moving data out of tusd's bucket.

    Return kwargs for SetStepParams.
    """
    # SECURITY: we expect metadata to come from Workbench itself. (On
    # production, there's no route from the Internet to tusd's POST endpoint.)
    # However, let's cast to correct types just to be safe. If a miscreant
    # comes along, that'll cause a 500 error and we'll be notified. (Better
    # than sending untrusted data to Django ORM.)
    # Raise TypeError, KeyError, ValueError.
    filename = str(data["MetaData"]["filename"])
    api_token = str(data["MetaData"]["apiToken"])
    workflow_id = int(data["MetaData"]["workflowId"])
    step_slug = data["MetaData"]["stepSlug"]
    size = int(data["Size"])
    bucket = str(data["Storage"]["Bucket"])
    key = str(data["Storage"]["Key"])

    if bucket != s3.TusUploadBucket:
        # security: if a hijacker manages to craft a request here, prevent its
        # creator from copying a file he/she can't see. (The creator is only
        # known to be able to see `key` of `s3.TusUploadBucket`.)
        raise RuntimeError("SECURITY: did tusd send this request?")

    suffix = PurePath(filename).suffix
    file_uuid = str(uuid.uuid4())
    final_key = None

    with upload.locked_and_loaded_step(workflow_id, step_slug) as (
        workflow_lock,
        step,
        param_id_name,
    ):  # raise UploadError
        # Ensure upload's API token is the same as the one we sent tusd.
        #
        # This doesn't give security: an attacker can simulate a request from
        # tusd with api_token=None and it will look like a browser-initiated
        # one.
        #
        # It's for timing: if the user resets a module's API token, we should
        # disallow all prior uploads.
        if api_token:  # empty when React client uploads
            upload.raise_if_api_token_is_wrong(step, api_token)  # raise UploadError

        final_key = step.uploaded_file_prefix + str(file_uuid) + suffix

        # Tricky leak here: if there's an exception or crash, the transaction
        # is reverted. final_key will remain in S3 but the database won't point
        # to it.
        #
        # Not a huge deal, because `final_key` is in the Step's own directory.
        # The user can delete all leaked files by deleting the Step.
        s3.copy(
            s3.UserFilesBucket,
            final_key,
            f"{bucket}/{key}",
            MetadataDirective="REPLACE",
            ContentDisposition=s3.encode_content_disposition(filename),
            ContentType="application/octet-stream",
        )

        step.uploaded_files.create(
            name=filename, size=size, uuid=file_uuid, key=final_key
        )
        delete_old_files_to_enforce_storage_limits(step=step)
        s3.remove(bucket, key)

    return dict(
        workflow_id=workflow_id, step=step, new_values={param_id_name: file_uuid}
    )


# FIXME make this a separate web server: one that doesn't respond to
# outside-world HTTP requests.
#
# For now, for SECURITY, we must beware each request. It might be coming from
# the outside world! (On production, we forbid direct contact using the load
# balancer. But we must beware amalgamated attacks -- e.g., if another internal
# server somehow allows requests on the user's behalf....) If it's coming from
# the outside world, 500 error is the right approach: this is an internal
# server error and we'll be emailed about it
async def tusd_hooks(request: HttpRequest) -> JsonResponse:
    if request.headers["hook-name"] == "pre-finish":  # raise KeyError => 500 error
        data = json.loads(request.body)  # raise ValueError => 500 error
        upload_data = data["Upload"]  # raise KeyError => 500 error
        try:
            command_kwargs = await _finish_upload(upload_data)  # raise => 500 error
        except upload.UploadError as err:
            return JsonResponse(
                {"error": {"code": err.error_code, **err.extra_data}},
                status=err.status_code,
            )
        # After the cooperative lock ends, update the Step.
        # SetStepParams sends delta to Websockets clients and queues render.
        await commands.do(SetStepParams, **command_kwargs)

        return JsonResponse({})
    else:
        return JsonResponse({"error": {"code": "unhandled-hook"}}, status_code=400)


tusd_hooks.csrf_exempt = True  # Django 3.1 decorator isn't async-safe
