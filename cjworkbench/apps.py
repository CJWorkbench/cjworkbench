# Startup code
from django.apps import AppConfig

class WorkbenchConfig(AppConfig):
    name = 'cjworkbench'

    def ready(self):
        from django.contrib.sites.models import Site
        from . import settings

        providers = settings.CJW_SOCIALACCOUNT_SECRETS
        provider_fields = ('client_id', 'secret')
        current_site = Site.objects.get_current()
        dirty = False

        for provider in providers:
            defaults = {key: provider.get(key, None) for key in provider_fields}
            social_app, created = current_site.socialapp_set.get_or_create(
                provider=provider['provider'], name=provider['name'], defaults=defaults
            )
            if not created:
                for field in provider_fields:
                    if provider[field] is not getattr(social_app, field):
                        setattr(social_app, field, provider[field])
                        dirty = True
            if dirty:
                social_app.save()

