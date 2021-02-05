from django.template.response import TemplateResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from cjwstate.models import Step
from cjwstate.models.module_registry import MODULE_REGISTRY
from server.serializers import (
    JsonizeContext,
    jsonize_clientside_workflow,
    jsonize_clientside_step,
)


@xframe_options_exempt
def embed(request, step_id):
    try:
        step = Step.objects.get(pk=step_id, is_deleted=False)
    except Step.DoesNotExist:
        step = None

    if step:
        if not step.workflow:
            step = None
        elif not step.workflow.request_authorized_read(request):
            step = None
        else:
            try:
                module_zipfile = MODULE_REGISTRY.latest(step.module_id_name)
                if not module_zipfile.get_spec().html_output:
                    step = None
            except KeyError:
                step = None

    if step:
        ctx = JsonizeContext(
            user=None,
            user_profile=None,
            session=None,
            locale_id=request.locale_id,
            module_zipfiles={module_zipfile.module_id: module_zipfile},
        )
        init_state = {
            "workflow": jsonize_clientside_workflow(
                step.workflow.to_clientside(include_tab_slugs=False),
                ctx,
                is_init=True,
            ),
            "step": jsonize_clientside_step(step.to_clientside(), ctx),
        }
    else:
        init_state = {"workflow": None, "step": None}

    return TemplateResponse(request, "embed.html", {"initState": init_state})
