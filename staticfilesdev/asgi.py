"""ASGI app for serving static files.

We don't use Django runserver because it doesn't allow middleware, so it can't
add CORS headers.

Instead, we create a minimal ASGI server that wraps Django.
"""

import django
from django.contrib.staticfiles import views
from django.http import Http404, HttpRequest, HttpResponseNotFound


django.setup()


class OurHttpRequest(HttpRequest):
    def __init__(self, META):
        self.META = META


async def application(scope, receive, send):
    assert scope["type"] == "http"
    while (await receive())["more_body"]:
        pass
    meta = {}
    headers = dict(scope["headers"])
    if b"if-modified-since" in headers:
        meta["HTTP_IF_MODIFIED_SINCE"] = headers[b"if-modified-since"].decode("latin-1")
    request = OurHttpRequest(meta)
    try:
        django_response = views.serve(request, scope["path"])
    except Http404 as err:
        django_response = HttpResponseNotFound()
    await send(
        {
            "type": "http.response.start",
            "status": django_response.status_code,
            "headers": [
                (b"Access-Control-Allow-Origin", b"*"),
                *(
                    (k.encode("latin-1"), v.encode("latin-1"))
                    for k, v in django_response.items()
                ),
            ],
        }
    )
    if django_response.streaming:  # success
        for chunk in django_response:
            await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body"})
    else:
        await send({"type": "http.response.body", "body": django_response.content})
