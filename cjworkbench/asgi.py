import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cjworkbench.settings")

from django.conf import settings

if not settings.I_AM_TESTING:
    import django

    django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from django.urls import path, register_converter

from cjworkbench.middleware.i18n import SetCurrentLocaleAsgiMiddleware
from cjworkbench.middleware.lifespan import LifespanMiddleware
from server.converters import WorkflowIdOrSecretIdConverter
from server.websockets import WorkflowConsumer

register_converter(WorkflowIdOrSecretIdConverter, "workflow_id_or_secret_id")

# used in unit tests
_url_router = AuthMiddlewareStack(
    SetCurrentLocaleAsgiMiddleware(
        URLRouter(
            [
                path(
                    "workflows/<workflow_id_or_secret_id:workflow_id_or_secret_id>",
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
