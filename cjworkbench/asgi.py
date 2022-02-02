import os

from django.conf import settings

if not settings.I_AM_TESTING:
    import django

    django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from django.urls import path, register_converter

from cjworkbench.middleware.i18n import SetCurrentLocaleAsgiMiddleware
from cjworkbench.middleware.rabbitmqlifespan import RabbitmqLifespanMiddleware
from cjworkbench.sync import database_sync_to_async
from server.converters import WorkflowIdOrSecretIdConverter
from server.websockets import WorkflowConsumer

register_converter(WorkflowIdOrSecretIdConverter, "workflow_id_or_secret_id")


async def extra_init() -> None:
    """Load all modules on startup, or raise an Exception.

    This means starting a kernel and validating all static modules.
    Good reasons to load during startup:

    1. In dev mode, this reports errors in modules ASAP.
    2. In production, this warms up our cache so the first requests
       won't be served too slowly.
    """
    import cjwstate.modules
    from cjwstate.models.module_registry import MODULE_REGISTRY

    cjwstate.modules.init_module_system()
    await database_sync_to_async(MODULE_REGISTRY.all_latest)()


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


application = RabbitmqLifespanMiddleware(
    ProtocolTypeRouter(
        {
            "http": get_asgi_application(),
            "websocket": _url_router,
        }
    ),
    extra_init=extra_init,
)
