import asyncio
import functools


def xframe_options_exempt(view_func):
    """
    Modify a view function by setting a response variable that instructs
    XFrameOptionsMiddleware to NOT set the X-Frame-Options HTTP header. Usage:

    @xframe_options_exempt
    def some_view(request):
        ...

    [2020-12-22, adamhooper] This is async-compatible, unlike
    django.views.decorators.clickjacking.xframe_options_exempt. Nix it when the
    Django decorator becomes async-compatible.
    """

    if asyncio.iscoroutinefunction(view_func):

        async def wrapped_view(*args, **kwargs):
            resp = await view_func(*args, **kwargs)
            resp.xframe_options_exempt = True
            return resp

    else:

        def wrapped_view(*args, **kwargs):
            resp = view_func(*args, **kwargs)
            resp.xframe_options_exempt = True
            return resp

    return functools.wraps(view_func)(wrapped_view)
