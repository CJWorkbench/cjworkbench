from functools import wraps
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from server.models import Workflow


def lookup_workflow_for_read(pk: int, request: HttpRequest) -> Workflow:
    """
    Find a Workflow based on its id.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have read access.
    """
    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.request_authorized_read(request):
        raise PermissionDenied()

    return workflow


def lookup_workflow_for_write(pk: int, request: HttpRequest) -> Workflow:
    """
    Find a Workflow based on its id.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have write access.
    """
    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.request_authorized_write(request):
        raise PermissionDenied()

    return workflow


def lookup_workflow_for_owner(pk: int, request: HttpRequest) -> Workflow:
    """
    Find a Workflow based on its id.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user is not its owner.
    """
    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.request_authorized_owner(request):
        raise PermissionDenied()

    return workflow


def loads_workflow_for_read(f):
    """
    Provides `workflow` to a Django view.

    Usage:

        @loads_workflow_for_read
        def view_workflow(request, workflow, ...):
            # workflow is loaded and the user has access.
            return JsonResponse(workflow.id)

    `request` and `workflow_id` are the first and second positional arguments
    in the returned function.

    This method does _not_ cooperatively lock the workflow. That's because a
    cooperative lock means a database transaction, and request handlers might
    want to do something _after_ the database transaction is committed.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have read access.
    """

    @wraps(f)
    def wrapper(request: HttpRequest, *args, workflow_id: int, **kwargs):
        workflow = lookup_workflow_for_read(workflow_id, request)  # or raise
        return f(request, workflow, *args, **kwargs)

    return wrapper


def loads_workflow_for_write(f):
    """
    Provides `workflow` to a Django view.

    Usage:

        @loads_workflow_for_write
        def view_workflow(request, workflow, ...):
            # workflow is loaded and the user has access.
            workflow.save()
            return JsonResponse(workflow.id)

    `request` and `workflow_id` are the first and second positional arguments
    in the returned function.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have write access.
    """

    @wraps(f)
    def wrapper(request: HttpRequest, *args, workflow_id: int, **kwargs):
        workflow = lookup_workflow_for_write(workflow_id, request)  # or raise
        return f(request, workflow, *args, **kwargs)

    return wrapper


def loads_workflow_for_owner(f):
    """
    Provides `workflow` to a Django view.

    Usage:

        @loads_workflow_for_owner
        def view_workflow(request, workflow, ...):
            # workflow is loaded and the user has access.
            workflow.save()
            return JsonResponse(workflow.id)

    `request` and `workflow_id` are the first and second positional arguments
    in the returned function.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user is not its owner.
    """

    @wraps(f)
    def wrapper(request: HttpRequest, *args, workflow_id: int, **kwargs):
        workflow = lookup_workflow_for_owner(workflow_id, request)  # or raise
        return f(request, workflow, *args, **kwargs)

    return wrapper


def loads_workflow_for_owner(f):
    """
    Provides `workflow` to a Django view.

    Usage:

        @loads_workflow_for_owner
        def view_workflow(request, workflow, ...):
            # workflow is loaded and the user has access.
            workflow.save()
            return JsonResponse(workflow.id)

    `request` and `workflow_id` are the first and second positional arguments
    in the returned function.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user is not its owner.
    """

    @wraps(f)
    def wrapper(request: HttpRequest, *args, workflow_id: int, **kwargs):
        workflow = lookup_workflow_for_owner(workflow_id, request)  # or raise
        return f(request, workflow, *args, **kwargs)

    return wrapper


def loads_wf_module_for_read(f):
    """
    Provides `workflow, wf_module` to a Django view.

    Usage:

        @loads_wf_module_for_read
        def view_workflow(request, workflow, wf_module, ...):
            # workflow+wf_module are loaded and the user has access.
            return JsonResponse(wf_module.id)

    `request`, `workflow_id` and `wf_module_id` are the first positional
    arguments in the returned function.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have read access. Raise
    Http404 if the WfModule is deleted or not part of the Workflow.
    """

    @wraps(f)
    def wrapper(
        request: HttpRequest, *args, workflow_id: int, wf_module_id: int, **kwargs
    ):
        workflow = lookup_workflow_for_read(workflow_id, request)  # or raise
        wf_module = get_object_or_404(WfModule.live_in_workflow, pk=wf_module_id)
        return f(request, workflow, tab, *args, **kwargs)

    return wrapper


def loads_wf_module_for_write(f):
    """
    Provides `workflow, wf_module` to a Django view.

    Usage:

        @loads_wf_module_for_write
        def view_workflow(request, workflow, wf_module, ...):
            # workflow+wf_module are loaded and the user has access.
            wf_module.save()
            return JsonResponse(wf_module.id)

    `request`, `workflow_id` and `wf_module_id` are the first positional
    arguments in the returned function.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have write access. Raise
    Http404 if the WfModule is deleted or not part of the Workflow.
    """

    @wraps(f)
    def wrapper(
        request: HttpRequest, *args, workflow_id: int, wf_module_id: int, **kwargs
    ):
        workflow = lookup_workflow_for_write(workflow_id, request)  # or raise
        wf_module = get_object_or_404(WfModule.live_in_workflow, pk=wf_module_id)
        return f(request, workflow, tab, *args, **kwargs)

    return wrapper


def loads_tab_for_write(f):
    """
    Provides `workflow, tab` to a Django view.

    Usage:

        @loads_tab_for_write
        def view_workflow(request, workflow, tab, ...):
            # workflow+tab are loaded and the user has access.
            workflow.save()
            return JsonResponse(tab.slug)

    `request`, `workflow_id` are the first and second positional arguments
    in the returned function.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have write access. Raise
    Http404 if the Tab is deleted or not part of the Workflow.
    """

    @wraps(f)
    def wrapper(request: HttpRequest, *args, workflow_id: int, tab_id: int, **kwargs):
        workflow = lookup_workflow_for_write(workflow_id, request)  # or raise
        tab = get_object_or_404(workflow.live_tabs, pk=tab_id)
        return f(request, workflow, tab, *args, **kwargs)

    return wrapper
