import json
from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from server.minio import minio_client, StaticFilesBucket


BUCKET_POLICY =  json.dumps({
    "Version":"2012-10-17",
    "Statement":[
        {
            "Sid":"",
            "Effect":"Allow",
            "Principal":{"AWS":"*"},
            "Action":"s3:GetBucketLocation",
            "Resource":"arn:aws:s3:::" + StaticFilesBucket
        },
        {
            "Sid":"",
            "Effect":"Allow",
            "Principal":{"AWS":"*"},
            "Action":"s3:ListBucket",
            "Resource":"arn:aws:s3:::" + StaticFilesBucket
        },
        {
            "Sid":"",
            "Effect":"Allow",
            "Principal":{"AWS":"*"},
            "Action":"s3:GetObject",
            "Resource":"arn:aws:s3:::" + StaticFilesBucket + "/*"
        }
    ]
})


class Command(BaseCommand):
    # We bundle all these commands into one so we don't have to wait for django
    # startup five times.

    help = 'Run DB migrations, reload modules and upload static files to minio'

    def handle(self, *args, **options):
        # Migrate sites first, to create the site table that we then edit with
        # a migration.
        management.call_command('migrate', 'sites')
        management.call_command('migrate')

        management.call_command('load_socialaccounts')

        management.call_command('reload-internal-modules')

        # We only collectstatic on non-debug. On debug, we don't upload to
        # minio because we'd need to run collectstatic every reboot, which
        # would be too slow/complex-to-set-up.
        if not settings.DEBUG:
            management.call_command('collectstatic', '--no-input')
            minio_client.set_bucket_policy(StaticFilesBucket, BUCKET_POLICY)
