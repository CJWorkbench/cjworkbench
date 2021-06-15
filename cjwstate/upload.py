import base64
import contextlib
import hashlib
from typing import Any, Dict, ContextManager, NamedTuple, Tuple
from urllib.parse import urljoin

import httpx
from django.conf import settings

from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.models.step import Step
from cjwstate.models.workflow import Workflow


class UploadError(Exception):
    def __init__(
        self, status_code: int, error_code: str, extra_data: Dict[str, Any] = {}
    ):
        super().__init__(self, status_code, error_code, extra_data)
        self.status_code = status_code
        self.error_code = error_code
        self.extra_data = extra_data

    def __str__(self):
        # for unit tests
        return "UploadError<%d,%s>" % (self.status_code, self.error_code)


def raise_if_api_token_is_wrong(step: Step, api_token: str) -> None:
    """Raise on invalid auth data.

    Raise UploadError(403, "step-has-no-api-token") if Step Upload API is disabled.

    Raise UploadError(403, "authorization-bearer-token-invalid") on wrong `api_token`.

    A hash of the token is compared, to prevent leaking the token through a
    timing attack.
    """
    actual_token = step.file_upload_api_token
    if not actual_token:
        raise UploadError(403, "step-has-no-api-token")

    api_token_hash = hashlib.sha256(api_token.encode("utf-8")).digest()
    actual_token_hash = hashlib.sha256(actual_token.encode("utf-8")).digest()
    if api_token_hash != actual_token_hash or api_token != actual_token:
        raise UploadError(403, "authorization-bearer-token-invalid")


@contextlib.contextmanager
def locked_and_loaded_step(
    workflow_id: int, step_slug: str
) -> ContextManager[Tuple[Workflow, Step, str]]:
    """Yield `workflow`, `step` and `file_param_id_name`.

    SECURITY: the caller may want to test the Step's `file_upload_api_token`.

    Raise UploadError(404, "workflow-not-found") on missing/deleted Workflow.

    Raise UploadError(404, "step-not-found") on missing/deleted Step.

    Raise UploadError(400, "step-module-deleted") on code-less Step.

    Raise UploadError(400, "step-has-no-file-param") on a Step with no File param.
    """
    try:
        with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow:
            try:
                step = Step.live_in_workflow(workflow).get(slug=step_slug)
            except Step.DoesNotExist:
                raise UploadError(404, "step-not-found")

            try:
                module_zipfile = MODULE_REGISTRY.latest(step.module_id_name)
            except KeyError:
                raise UploadError(400, "step-module-deleted")

            try:
                file_param_id_name = next(
                    iter(
                        pf.id_name
                        for pf in module_zipfile.get_spec().param_fields
                        if pf.type == "file"
                    )
                )
            except StopIteration:
                raise UploadError(400, "step-has-no-file-param")

            yield workflow, step, file_param_id_name
    except Workflow.DoesNotExist:
        raise UploadError(404, "workflow-not-found")


async def create_tus_upload(
    *, workflow_id: int, step_slug: str, api_token: str, filename: str, size: int
) -> str:
    """Create a URL for end users.

    Raise on error communicating with tusd.
    """

    if not settings.TUS_CREATE_UPLOAD_URL:
        raise RuntimeError("Environment error: you must set TUS_CREATE_UPLOAD_URL")

    upload_metadata_header = b"apiToken %s,filename %s,workflowId %s,stepSlug %s" % (
        # We include apiToken: after a user resets apiToken, prior API uploads
        # must break. Rely on storage-layer encryption to encrypt the API token,
        # and on object lifecycle to delete the API token reasonably swiftly.
        # Assume that users can't guess the response location: therefore, the
        # only users who can access the location (and thus read the API token
        # from a HEAD response header) are the ones who already have the API
        # token.
        #
        # The apiToken is empty when users authenticate via session. Don't put
        # apiToken last, so the header never ends with b' ' (which is invalid).
        base64.b64encode(api_token.encode("utf-8")),
        base64.b64encode(filename.encode("utf-8")),
        base64.b64encode(str(workflow_id).encode("utf-8")),
        base64.b64encode(step_slug.encode("utf-8")),
    )
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.TUS_CREATE_UPLOAD_URL,
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Length": str(size).encode("utf-8"),
                "Upload-Metadata": upload_metadata_header,
            },
        )  # raise all sorts of errors
        if response.status_code != 201:
            raise RuntimeError("Unexpected TUS response: %r" % response)

    # TUS spec says the server may return a relative path
    original_tus_upload_url = urljoin(
        settings.TUS_CREATE_UPLOAD_URL, response.headers["location"]
    )

    # TUS_CREATE_UPLOAD_URL is only visible on our intranet (where it isn't
    # firewalled away). Give customers the Internet-visible URL.
    tus_upload_url = original_tus_upload_url.replace(
        settings.TUS_CREATE_UPLOAD_URL, settings.TUS_EXTERNAL_URL_PREFIX_OVERRIDE
    )

    return tus_upload_url
