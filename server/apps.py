# Startup code
from django.apps import AppConfig

class ServerConfig(AppConfig):
    name = 'server'

    def ready(self):
        import server.example_workflows         # register User post_save handler
