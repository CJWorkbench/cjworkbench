import json
from typing import Callable

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

from cjwstate.models import AclEntry, Workflow
from cjwstate.models.fields import Role

# access-control lists


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


class Entry(View):
    form_class = AclEntryForm

    def put(self, request: HttpRequest, workflow_id: int, *, email: str):
        """Set a user's access to a Workflow."""
        workflow = lookup_workflow_and_auth(
            Workflow.request_authorized_owner, workflow_id, request
        )
        if workflow.is_anonymous:
            return JsonResponse({"error": "cannot-share-anonymous"}, status=404)

        try:
            data = json.loads(request.body, encoding="utf-8")
        except ValueError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        form = self.form_class({**data, "email": email})
        if not form.is_valid():
            return HttpResponse(
                '{"errors":' + form.errors.as_json() + "}",
                content_type="application/json",
                status=400,
            )

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
        workflow = lookup_workflow_and_auth(
            Workflow.request_authorized_owner, workflow_id, request
        )
        if workflow.is_anonymous:
            return JsonResponse({"error": "cannot-share-anonymous"}, status=404)

        # validate email (use dummy role)
        form = self.form_class({"role": Role.VIEWER.value, "email": email})
        if not form.is_valid():
            return HttpResponse(
                '{"errors":' + form.errors.as_json() + "}",
                content_type="application/json",
                status=400,
            )

        if form.cleaned_data["email"] == workflow.owner.email:
            return JsonResponse({"errors": "cannot-share-with-owner"}, status=400)

        AclEntry.objects.filter(workflow=workflow, email=email).delete()
        return HttpResponse(status=204)
