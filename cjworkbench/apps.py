# Startup code
from django.apps import AppConfig


class ServerConfig(AppConfig):
    name = 'cjworkbench'

    def ready(self):
        pass
