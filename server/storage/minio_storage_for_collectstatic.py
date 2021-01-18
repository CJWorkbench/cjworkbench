import concurrent.futures
import gzip
import logging
import mimetypes
from queue import Queue
from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage
from cjwstate.minio import client, StaticFilesBucket


logger = logging.getLogger(__name__)


class MinioStorage(Storage):
    def __init__(self, *args, **kwargs):
        Storage.__init__(self, *args, **kwargs)

    """Dumb class for uploading straight to S3."""

    def _upload_in_thread(self, name: str, data: bytes) -> None:
        """
        Perform the actual upload.

        Raise an exception if the file is not certainly uploaded.
        """

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
            **kwargs,
        )
        logger.info("Finished uploading %s (%d bytes)" % (name, len(data)))

    def save(self, name: str, file: File, max_length=None) -> None:
        """
        *Start* uploading `file` to S3.

        Return before finish.
        """
        if not hasattr(self, "_executor"):
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=10, thread_name_prefix="collectstatic"
            )
            self._upload_futures = []

        # The caller is about to _close_ `file`. So let's read all the data
        # into RAM while we still can. Good thing these files are small, right?
        data = file.read()
        self._upload_futures.append(
            self._executor.submit(self._upload_in_thread, name, data)
        )

    def post_process(self, *args, **kwargs) -> None:
        """
        Wait for all started uploads to finish, then clean up.

        Log and raise an exception if any of the uploads fail.
        """
        error = False
        for future in concurrent.futures.as_completed(self._upload_futures):
            try:
                future.result()
            except Exception:
                logger.exception("Exception during upload of a file")
                error = True
        self._executor.shutdown(True)
        del self._executor
        del self._upload_futures

        if error:
            raise OSError("Failed to upload all the files")

        return []  # because Django expects a list of postprocessed files

    def delete(self, name):
        # We never want to delete
        pass

    def exists(self, name):
        # We always want to overwrite
        return False

    def url(self, name):
        return settings.STATIC_URL + name
