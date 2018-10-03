import json
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from server.models import AclEntry, Workflow
from server.serializers import AclEntrySerializer
from .auth import loads_workflow_for_read, loads_workflow_for_owner

# access-control lists

class List(View):
    @method_decorator(loads_workflow_for_read)
    def get(self, request: HttpRequest, workflow: Workflow):
        if workflow.is_anonymous:
            return JsonResponse({'error': 'cannot-share-anonymous'},
                                status=404)

        entries = workflow.acl.order_by('email').all()
        serializer = AclEntrySerializer(entries, many=True)
        return JsonResponse(serializer.data, safe=False)


class AclEntryForm(ModelForm):
    class Meta:
        model = AclEntry
        fields = ('email', 'can_edit')


class Entry(View):
    form_class = AclEntryForm

    @method_decorator(loads_workflow_for_owner)
    def put(self, request: HttpRequest, workflow: Workflow, *, email: str):
        """Set a user's access to a Workflow."""
        if workflow.is_anonymous:
            return JsonResponse({'error': 'cannot-share-anonymous'},
                                status=404)

        try:
            data = json.loads(request.body, encoding='utf-8')
        except ValueError as err:
            return JsonResponse({'error': 'invalid JSON'}, status=400)

        form = self.form_class({**data, 'email': email})
        if not form.is_valid():
            return HttpResponse('{"errors":' + form.errors.as_json() + '}',
                                content_type='application/json', status=400)

        if form.cleaned_data['email'] == workflow.owner.email:
            return JsonResponse({'errors': 'cannot-share-with-owner'},
                                status=400)

        AclEntry.objects.update_or_create(
            workflow=workflow,
            email=form.cleaned_data['email'],
            defaults={'can_edit': form.cleaned_data['can_edit']}
        )

        return HttpResponse(status=204)

    @method_decorator(loads_workflow_for_owner)
    def delete(self, request: HttpRequest, workflow: Workflow, *, email: str):
        """Remove a user's access to a Workflow."""
        if workflow.is_anonymous:
            return JsonResponse({'error': 'cannot-share-anonymous'},
                                status=404)

        # validate email
        form = self.form_class({'can_edit': False, 'email': email})
        if not form.is_valid():
            return HttpResponse('{"errors":' + form.errors.as_json() + '}',
                                content_type='application/json', status=400)

        if form.cleaned_data['email'] == workflow.owner.email:
            return JsonResponse({'errors': 'cannot-share-with-owner'},
                                status=400)

        AclEntry.objects.filter(workflow=workflow, email=email).delete()
        return HttpResponse(status=204)
