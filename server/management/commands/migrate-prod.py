from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand
from cjwstate import minio


STATIC_FILES_BUCKET_POLICY = """{
    "Version":"2012-10-17",
    "Statement":[
        {
            "Sid":"",
            "Effect":"Allow",
            "Principal":{"AWS":"*"},
            "Action":"s3:GetBucketLocation",
            "Resource":"arn:aws:s3:::BUCKET"
        },
        {
            "Sid":"",
            "Effect":"Allow",
            "Principal":{"AWS":"*"},
            "Action":"s3:ListBucket",
            "Resource":"arn:aws:s3:::BUCKET"
        },
        {
            "Sid":"",
            "Effect":"Allow",
            "Principal":{"AWS":"*"},
            "Action":"s3:GetObject",
            "Resource":"arn:aws:s3:::BUCKET/*"
        }
    ]
}""".replace(
    "BUCKET", minio.StaticFilesBucket
)


class Command(BaseCommand):
    # We bundle all these commands into one so we don't have to wait for django
    # startup five times.

    help = "Run DB migrations, reload modules and upload static files to minio"

    def handle(self, *args, **options):
        # We only collectstatic on non-debug. On debug, we don't upload to
        # minio because we'd need to run collectstatic every reboot, which
        # would be too slow/complex-to-set-up.
        if not settings.DEBUG:
            management.call_command("collectstatic", "--no-input")

        minio.ensure_bucket_exists(minio.UserFilesBucket)
        minio.ensure_bucket_exists(minio.StoredObjectsBucket)
        minio.ensure_bucket_exists(minio.ExternalModulesBucket)
        minio.ensure_bucket_exists(minio.CachedRenderResultsBucket)

        # ICK ugly hack. TODO there must be a better place to make uploaded
        # files readable for integration tests....
        if settings.MINIO_BUCKET_PREFIX == "integrationtest":
            minio.ensure_bucket_exists(minio.StaticFilesBucket)
            minio.client.put_bucket_policy(
                Bucket=minio.StaticFilesBucket, Policy=STATIC_FILES_BUCKET_POLICY
            )
            # No need to enable CORS for minio-served buckets:
            # "Minio enables CORS by default on all buckets for all HTTP verbs"
            # https://docs.min.io/docs/minio-server-limits-per-tenant.html

        # Migrate comes last: during deploy, in some cases, migration can make
        # the site unusable until it's completed. So don't add any instructions
        # _after_ this, because that will increase our downtime if we're
        # unfortunate enough to cause downtime.
        management.call_command("migrate")
