from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand
from cjwstate import s3


class Command(BaseCommand):
    # We bundle all these commands into one so we don't have to wait for django
    # startup five times.
    help = "Run DB migrations, reload modules and upload static files to s3"

    def handle(self, *args, **options):
        # We only collectstatic on non-debug. On debug, we don't upload to
        # s3 because we'd need to run collectstatic every reboot, which
        # would be too slow/complex-to-set-up.
        if not settings.DEBUG:
            management.call_command("collectstatic", "--no-input")

        # Migrate comes last: during deploy, in some cases, migration can make
        # the site unusable until it's completed. So don't add any instructions
        # _after_ this, because that will increase our downtime if we're
        # unfortunate enough to cause downtime.
        management.call_command("migrate")
