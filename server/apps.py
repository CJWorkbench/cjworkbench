# Startup code
from django.apps import AppConfig
from django.conf import settings


class ServerConfig(AppConfig):
    name = 'server'


    def ready(self):
        import server.example_workflows         # register User post_save handler

        # load internal modules into DB, once
        if not settings.I_AM_TESTING:
            from server.initmodules import init_modules
            init_modules()
