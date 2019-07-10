from django.core.management.base import BaseCommand, CommandError
from server import maintenance


class Command(BaseCommand):
    help = "Delete all Workflows that have no owner and no active session"

    def handle(self, *args, **options):
        maintenance.delete_expired_anonymous_workflows()
