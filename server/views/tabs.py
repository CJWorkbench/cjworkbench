from django import forms
from django.http import HttpRequest, HttpResponseForbidden, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from server.models.commands import AddModuleCommand
from server.models import Module, Tab, Workflow
from .auth import loads_tab_for_write


class AddModuleForm(forms.Form):
    position = forms.IntegerField()
    module = forms.ModelChoiceField(queryset=Module.objects)
    params = forms.Field(required=False)  # allow empty params

class AddModule(View):
    @method_decorator(loads_tab_for_write)
    def post(self, request: HttpRequest, workflow: Workflow, tab: Tab):
        form = AddModuleForm(request.POST)
        if not form.is_valid():
            return Response({'errors': form.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        data = form.cleaned_data
        position = data.position
        module_version = data.module.module_versions.last()
        param_values = data.params or {}

        delta = async_to_sync(AddModuleCommand.create)(
            workflow=workflow,
            tab=tab,
            module_version=module_version,
            order=position,
            param_values=param_values
        )
        serializer = WfModuleSerializer(delta.wf_module)
        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
