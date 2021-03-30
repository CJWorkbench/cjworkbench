"""Access Control List endpoints."""
import contextlib
import json
import math
import secrets
import string
from typing import Callable, ContextManager

from django import forms
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from cjwstate.models.acl_entry import AclEntry
from cjwstate.models.fields import Role
from cjwstate.models.workflow import DbObjectCooperativeLock, Workflow

ALPHABET = string.ascii_letters + string.digits
N_BITS_ENTROPY = 160  # kinda arbitrary, inspired by RFC4226 and SHA1
N_BYTES_SECRET = math.ceil(160 / math.log2(len(ALPHABET)))


def generate_secret_id():
    """Generate a secure, unique, secret ID for a workflow.

    The ID looks like "w[a-zA-Z0-9]+".
    """
    return "w" + "".join(secrets.choice(ALPHABET) for i in range(N_BYTES_SECRET))


@contextlib.contextmanager
def authenticated_owned_workflow(
    request: HttpRequest, workflow_id: int
) -> ContextManager[DbObjectCooperativeLock]:
    """Find a Workflow based on its ID, with request owner as owner.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    request user is not the owner (or if the request user is anonymous).
    """
    with contextlib.ExitStack() as stack:
        try:
            workflow_lock = stack.enter_context(
                Workflow.authorized_lookup_and_cooperative_lock(
                    "owner", user=request.user, session=None, id=workflow_id
                )
            )
        except Workflow.DoesNotExist as err:
            if err.args[0].endswith("access denied"):
                raise PermissionDenied()
            raise Http404()
        yield workflow_lock


def lookup_workflow_and_auth(
    auth: Callable[[Workflow, HttpRequest], None], pk: int, request: HttpRequest
) -> Workflow:
    """Find a Workflow based on its id.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have access.
    """
    workflow = get_object_or_404(Workflow, pk=pk)

    if not auth(workflow, request):
        raise PermissionDenied()

    return workflow


class AclEntryForm(forms.Form):
    email = forms.EmailField()
    role = forms.TypedChoiceField(
        choices=[(v.value, v.value) for v in Role], coerce=Role, empty_value=Role.VIEWER
    )


class AclIndexForm(forms.Form):
    public = forms.BooleanField(required=False)
    has_secret = forms.BooleanField(required=False)


class Index(View):
    def put(self, request: HttpRequest, workflow_id: int):
        """Set public access to a Workflow."""
        try:
            data = json.loads(request.body, encoding="utf-8")
        except ValueError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        form = AclIndexForm(data)
        if not form.is_valid():
            return JsonResponse(
                {"error": "bad-request", "messages": form.errors.as_json()}
            )

        with authenticated_owned_workflow(request, workflow_id) as workflow_lock:
            workflow = workflow_lock.workflow
            workflow.public = form.cleaned_data["public"]
            if form.cleaned_data["has_secret"]:
                if not workflow.secret_id:
                    if (
                        not request.user.user_profile.effective_limits.can_create_secret_link
                    ):
                        return JsonResponse(
                            {"error": "you must pay for this feature"}, status=403
                        )
                    workflow.secret_id = generate_secret_id()
            else:
                workflow.secret_id = ""
            workflow.save(update_fields=["public", "secret_id"])

        return JsonResponse(
            {"workflow": {"public": workflow.public, "secret_id": workflow.secret_id}}
        )


class Entry(View):
    def put(self, request: HttpRequest, workflow_id: int, *, email: str):
        """Set a user's access to a Workflow."""
        try:
            data = json.loads(request.body, encoding="utf-8")
        except ValueError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        form = AclEntryForm({**data, "email": email})
        if not form.is_valid():
            return HttpResponse(
                '{"errors":' + form.errors.as_json() + "}",
                content_type="application/json",
                status=400,
            )

        with authenticated_owned_workflow(request, workflow_id) as workflow_lock:
            workflow = workflow_lock.workflow

            if form.cleaned_data["email"] == workflow.owner.email:
                return JsonResponse({"errors": ["cannot-share-with-owner"]}, status=400)

            AclEntry.objects.update_or_create(
                workflow=workflow,
                email=form.cleaned_data["email"],
                defaults={"role": Role(form.cleaned_data["role"])},
            )

            return HttpResponse(status=204)

    def delete(self, request: HttpRequest, workflow_id: int, *, email: str):
        """Remove a user's access to a Workflow."""
        # validate email (use dummy role)
        form = AclEntryForm({"role": Role.VIEWER.value, "email": email})
        if not form.is_valid():
            return HttpResponse(
                '{"errors":' + form.errors.as_json() + "}",
                content_type="application/json",
                status=400,
            )

        with authenticated_owned_workflow(request, workflow_id) as workflow_lock:
            workflow = workflow_lock.workflow

            if form.cleaned_data["email"] == workflow.owner.email:
                return JsonResponse({"errors": "cannot-share-with-owner"}, status=400)

            AclEntry.objects.filter(workflow=workflow, email=email).delete()
            return HttpResponse(status=204)
