"""
ASGI config for cjworkbench project.

Used for websockets
"""

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


def create_url_router() -> AuthMiddlewareStack:
    return AuthMiddlewareStack(
        URLRouter([url(r"workflows/(?P<workflow_id>\d+)", WorkflowConsumer)])
    )


def create_application() -> ProtocolTypeRouter:
    """Create an ASGI application."""
    return ProtocolTypeRouter({"websocket": AuthMiddlewareStack(create_url_router())})


application = create_application()
