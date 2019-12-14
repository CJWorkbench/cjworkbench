# Startup code
from django.apps import AppConfig


class ServerConfig(AppConfig):
    name = "server"

    def ready(self):
        # monkey-patch FacebookProvider
        from allauth.socialaccount.providers.facebook.provider import FacebookProvider
        from django.core.exceptions import ImproperlyConfigured

        old_media_js = FacebookProvider.media_js

        def new_media_js(self, request):
            try:
                return old_media_js(self, request)
            except ImproperlyConfigured:
                return ""

        FacebookProvider.media_js = new_media_js
