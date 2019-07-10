import gzip
import io
import mimetypes
from django.conf import settings
from django.core.files.storage import Storage
from server.minio import ensure_bucket_exists, client, StaticFilesBucket


class MinioStorage(Storage):
    def __init__(self, *args, **kwargs):
        Storage.__init__(self, *args, **kwargs)
        ensure_bucket_exists(StaticFilesBucket)

    """Dumb class for uploading straight to S3."""

    def _save(self, name, file) -> None:
        # TODO django 2.0: with file.open('wb') as f:
        file.open("rb")
        try:
            data = file.read()
        finally:
            file.close()

        content_type, _ = mimetypes.guess_type(name, strict=False)
        content_type = content_type or "application/octet-stream"

        kwargs = {}
        if content_type.startswith("text") or content_type.split("/")[1] in (
            "xml",
            "json",
            "javascript",
        ):
            data = gzip.compress(data)
            kwargs["ContentEncoding"] = "gzip"

        client.put_object(
            Body=data,
            Bucket=StaticFilesBucket,
            Key=name,
            ContentLength=len(data),
            ContentType=content_type,
            # These are static files, but only Webpack-generated files have
            # hashed filenames. Logos and whatnot don't. So let's tell the
            # browser to cache for one day, to time-bound the damage when we
            # deploy a new version of our logo and users keep the old one.
            CacheControl="public, max-age=86400",
            **kwargs
        )

    def delete(self, name):
        # We never want to delete
        pass

    def exists(self, name):
        # We always want to overwrite
        return False

    def url(self, name):
        return settings.STATIC_URL + name
