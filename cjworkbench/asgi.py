"""
ASGI config for cjworkbench project.

Used for websockets
"""

import asyncio
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cjworkbench.settings")

from django.conf import settings

if not settings.I_AM_TESTING:
    import django

    django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.conf.urls import url

from server.websockets import WorkflowConsumer
from cjwstate.models.module_registry import MODULE_REGISTRY
import cjwstate.modules
from cjworkbench.middleware.i18n import SetCurrentLocaleAsgiMiddleware
from cjworkbench.sync import database_sync_to_async


def create_url_router() -> AuthMiddlewareStack:
    return AuthMiddlewareStack(
        URLRouter([url(r"workflows/(?P<workflow_id>\d+)", WorkflowConsumer)])
    )


def create_application() -> ProtocolTypeRouter:
    """Create an ASGI application."""
    # Load static modules on startup.
    #
    # This means starting a kernel and validating all static modules. There are
    # two good reasons to load during startup:
    #
    # 1. In dev mode, this reports errors in modules ASAP -- during startup
    # 2. In production, this import line costs time -- better to incur that
    #    cost during startup than to incur it when responding to some random
    #    request.
    cjwstate.modules.init_module_system()
    if not settings.I_AM_TESTING:
        # Only the test environment, Django runs migrations itself. We can't
        # use MODULE_REGISTRY until it migrates.
        #
        # If we're loading from uvicorn, this is run within uvicorn.Server's
        # `async def serve()`. Avoid SynchronousOnlyOperation.
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "just for now"
        MODULE_REGISTRY.all_latest()
        del os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"]

    return ProtocolTypeRouter(
        {
            "websocket": AuthMiddlewareStack(
                SetCurrentLocaleAsgiMiddleware(create_url_router())
            )
        }
    )


application = create_application()
