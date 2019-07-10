# Startup code
from django.apps import AppConfig


class ServerConfig(AppConfig):
    name = "server"

    def ready(self):
        pass
