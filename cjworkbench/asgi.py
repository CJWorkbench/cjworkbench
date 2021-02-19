import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cjworkbench.settings")

from django.conf import settings

if not settings.I_AM_TESTING:
    import django

    django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.conf.urls import url
from django.core.asgi import get_asgi_application

from cjworkbench.middleware.i18n import SetCurrentLocaleAsgiMiddleware
from cjworkbench.middleware.lifespan import LifespanMiddleware
from server.websockets import WorkflowConsumer


# used in unit tests
_url_router = AuthMiddlewareStack(
    SetCurrentLocaleAsgiMiddleware(
        URLRouter(
            [
                url(
                    r"workflows/(?P<workflow_id>\d+)",
                    WorkflowConsumer.as_asgi(),
                )
            ]
        )
    )
)


application = LifespanMiddleware(
    ProtocolTypeRouter(
        {
            "http": get_asgi_application(),
            "websocket": _url_router,
        }
    )
)
