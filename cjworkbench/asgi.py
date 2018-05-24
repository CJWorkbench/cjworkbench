"""
ASGI config for cjworkbench project.

Used for websockets
"""

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.conf.urls import url
import os

from server.websockets import WorkflowConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cjworkbench.settings")

def create_url_router() -> AuthMiddlewareStack:
    return AuthMiddlewareStack(URLRouter([
        url(r'workflows/(?P<workflow_id>\d+)', WorkflowConsumer),
    ]))

def create_application() -> ProtocolTypeRouter:
    """Create an ASGI application."""
    return ProtocolTypeRouter({
        'websocket': AuthMiddlewareStack(create_url_router()),
    })

application = create_application()
