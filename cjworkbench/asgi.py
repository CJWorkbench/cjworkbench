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

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter([
            url(r'workflows/(?P<workflow_id>\d+)', WorkflowConsumer),
        ])
    ),
})
