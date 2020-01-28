# Startup code
from django.apps import AppConfig


class ServerConfig(AppConfig):
    name = "cjworkbench"

    def ready(self):
        import cjworkbench.signals
        #from cjworkbench.i18n.trans import MESSAGE_LOCALIZER_REGISTRY

        #MESSAGE_LOCALIZER_REGISTRY.update_supported_modules()
