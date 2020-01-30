from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.decorators import api_view
from cjwstate.importmodule import WorkbenchModuleImportError, import_module_from_url
from cjwstate.models.module_registry import MODULE_REGISTRY
from server.serializers import JsonizeContext, jsonize_clientside_module


@api_view(["POST"])
@login_required
def import_from_github(request):
    if not request.user.is_staff:
        return JsonResponse(
            {"error": "Only an admin can call this method"},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        clientside_module, module_zipfile = import_module_from_url(request.data["url"])
        ctx = JsonizeContext(
            request.user,
            request.session,
            request.locale_id,
            {module_zipfile.module_id: module_zipfile},
        )
        data = jsonize_clientside_module(clientside_module, ctx)
        return JsonResponse(data, status=status.HTTP_201_CREATED)
    except WorkbenchModuleImportError as err:
        # Respond with 200 OK so the client side can read the error message.
        # TODO make the client smarter
        return JsonResponse({"error": str(err)}, status=status.HTTP_200_OK)
