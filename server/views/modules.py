from django.http import Http404, HttpRequest, HttpResponse

from cjworkbench.middleware.clickjacking import xframe_options_exempt
from cjworkbench.sync import database_sync_to_async
from cjwstate.models.module_registry import MODULE_REGISTRY


@xframe_options_exempt
async def module_html(request: HttpRequest, module_slug: str):
    # raise Http404
    try:
        module_zipfile = await database_sync_to_async(MODULE_REGISTRY.latest)(
            module_slug
        )
        html = module_zipfile.get_optional_html()
    except KeyError:
        raise Http404()
    if html is None:
        raise Http404()
    return HttpResponse(content=html)
