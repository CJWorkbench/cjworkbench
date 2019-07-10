from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from cjworkbench import settings


class Command(BaseCommand):
    help = "Loads the social accounts (with secrets) from the config file"

    def handle(self, *args, **options):
        current_site = Site.objects.get_current()
        providers = settings.CJW_SOCIALACCOUNT_SECRETS
        provider_fields = ("client_id", "secret")
        dirty = False

        if len(providers) == 0:
            self.stdout.write("No social account providers found")
            return

        for provider in providers:
            defaults = {key: provider.get(key, None) for key in provider_fields}
            social_app, created = current_site.socialapp_set.get_or_create(
                provider=provider["provider"], name=provider["name"], defaults=defaults
            )
            if not created:
                self.stdout.write(
                    self.style.SUCCESS(
                        'Found existing "%s" provider config' % provider["provider"]
                    )
                )
                for field in provider_fields:
                    if provider[field] != getattr(social_app, field):
                        self.stdout.write(
                            self.style.SUCCESS('Updating "%s" field' % field)
                        )
                        setattr(social_app, field, provider[field])
                        dirty = True
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        'Created new "%s" provider config' % provider["provider"]
                    )
                )

            if dirty:
                self.stdout.write(
                    self.style.SUCCESS(
                        'Saving "%s" provider config' % provider["provider"]
                    )
                )
                social_app.save()
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        'No changes to "%s" provider config' % provider["provider"]
                    )
                )
