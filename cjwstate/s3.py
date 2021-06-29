"""High-level storage backed by AWS S3, Google GCS, or Minio.
"""

import errno
import json
import logging
import pathlib
import sys
import urllib3
import urllib.parse
from contextlib import contextmanager
from typing import ContextManager, NamedTuple

import boto3
import botocore
from boto3.s3.transfer import S3Transfer, TransferConfig
from django.conf import settings

from cjwkernel.util import tempfile_context


logger = logging.getLogger(__name__)


def encode_content_disposition(filename: str) -> str:
    """Build a Content-Disposition header value for the given filename."""
    enc_filename = urllib.parse.quote(filename, encoding="utf-8")
    return "attachment; filename*=UTF-8''" + enc_filename


class Layer:
    def __init__(self):
        self._client = None
        self._uploader = None
        self._downloader = None

    @property
    def client(self):
        """Singleton S3 client for API operations."""
        if self._client is None:
            session = boto3.session.Session(region_name="us-east-1")
            self._client = session.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT,  # e.g., 'https://localhost:9001/'
                config=botocore.client.Config(max_pool_connections=50),
            )
        return self._client

    @property
    def downloader(self):
        """Singleton S3 "downloader" for all downloads.

        All concurrent downloads reuse the same thread pool. This caps the number of
        threads S3 uses.
        """
        if self._downloader is None:
            self._downloader = S3Transfer(self.client, TransferConfig())
        return self._downloader

    @property
    def uploader(self):
        """Upload configuration.

        To support Google Cloud Storage, we disable multipart uploads. Every upload
        uses the calling thread and uploads in a single part.
        """
        if self._uploader is None:
            self._uploader = S3Transfer(
                self.client,
                TransferConfig(use_threads=False, multipart_threshold=sys.maxsize),
            )
        return self._uploader

    @property
    def error(self):
        """Namespace for exceptions.

        Usage:

            from cjwstate import s3

            try:
                s3.layer.client.head_bucket(Bucket='foo')
            except s3.layer.error.NoSuchBucket as err:
                print(repr(err))
        """
        # boto3 exceptions are a bit odd -- https://github.com/boto/boto3/issues/1195
        return self.client.exceptions


layer = Layer()


UserFilesBucket = settings.S3_BUCKET_NAME_PATTERN % "user-files"
StoredObjectsBucket = settings.S3_BUCKET_NAME_PATTERN % "stored-objects"
ExternalModulesBucket = settings.S3_BUCKET_NAME_PATTERN % "external-modules"
CachedRenderResultsBucket = settings.S3_BUCKET_NAME_PATTERN % "cached-render-results"
TusUploadBucket = settings.S3_BUCKET_NAME_PATTERN % "upload"


def list_file_keys(bucket: str, prefix: str):
    """List keys of non-directory objects, non-recursively, in `prefix`.

    >>> s3.list_file_keys('bucket', 'filter/a132b3f/')
    ['filter/a132b3f/spec.json', 'filter/a132b3f/filter.py']
    """
    # Use list_objects, not list_objects_v2, because Google Cloud Storage's
    # AWS emulation doesn't support v2.
    response = layer.client.list_objects(
        Bucket=bucket, Prefix=prefix, Delimiter="/"  # avoid recursive
    )
    if response.get("IsTruncated"):
        # ... I guess we should paginate?
        raise NotImplementedError("list_objects() returned truncated result")
    return [o["Key"] for o in response.get("Contents", [])]


def fput_file(bucket: str, key: str, path: pathlib.Path) -> None:
    layer.uploader.upload_file(str(path.resolve()), bucket, key)


def put_bytes(bucket: str, key: str, body: bytes, **kwargs) -> None:
    layer.client.put_object(
        Bucket=bucket, Key=key, Body=body, ContentLength=len(body), **kwargs
    )


def exists(bucket: str, key: str) -> bool:
    try:
        layer.client.head_object(Bucket=bucket, Key=key)
        return True
    except layer.error.NoSuchKey:
        return False
    except layer.error.ClientError as err:
        # Botocore 1.12.130 seems to raise ClientError instead of NoSuchKey
        if err.response["Error"]["Code"] == "404":
            return False
        raise


class Stat(NamedTuple):
    size: int


def stat(bucket: str, key: str) -> Stat:
    """Return an object's metadata or raise an error."""
    response = layer.client.head_object(Bucket=bucket, Key=key)
    return Stat(response["ContentLength"])


def remove(bucket: str, key: str) -> None:
    """Delete the file. No-op if it is already deleted."""
    try:
        layer.client.delete_object(Bucket=bucket, Key=key)
    except layer.error.NoSuchKey:
        pass


def copy(bucket: str, key: str, copy_source: str, **kwargs) -> None:
    layer.client.copy_object(Bucket=bucket, Key=key, CopySource=copy_source, **kwargs)


def _remove_by_prefix(bucket: str, prefix: str, force=False) -> None:
    """Remove all objects in `bucket` whose keys begin with `prefix`.

    This is _not atomic_. An aborted delete may leave some objects deleted
    and others not-deleted.

    It's also slow. Be certain there aren't many files to delete.

    If you mean to use a directory-style `prefix` -- that is, one that ends in
    `"/"` -- then use `remove_recursive()` to signal your intent.

    If you really mean to use `prefix=''` -- which will wipe the entire
    bucket -- pass `force=True`. Otherwise, this function raises ValueError
    when `prefix=''`.
    """
    if prefix in ("/", "") and not force:
        raise ValueError("Refusing to remove prefix=/ when force=False")

    # Use list_objects, not list_objects_v2, because Google Cloud Storage's
    # AWS emulation doesn't support v2.
    #
    # Loop, deleting 1,000 keys at a time. S3 DELETE is strongly-consistent:
    # after we delete 1,000 keys, we're guaranteed list_objects() won't re-list
    # them. Same with Google Cloud Storage, which we configure to emulate AWS on
    # production.
    #
    # ref: https://docs.aws.amazon.com/AmazonS3/latest/dev/Introduction.html#ConsistencyModel
    # ref: https://cloud.google.com/storage/docs/consistency#strongly_consistent_operations
    # ref: https://cloud.google.com/storage/docs/interoperability
    done = False
    while not done:
        # no Delimiter="/" means it's a recursive request
        list_response = layer.client.list_objects(Bucket=bucket, Prefix=prefix)
        done = not list_response.get("IsTruncated", False)
        keys = [o["Key"] for o in list_response.get("Contents", [])]
        # Use layer.client.delete_object(), not delete_objects(), because Google Cloud
        # Storage doesn't emulate DeleteObjects.
        #
        # This is slow. But so is multi-delete through s3, because s3's
        # GCS gateway deletes one-at-a-time anyway.
        for key in keys:
            remove(bucket, key)


def remove_recursive(bucket: str, prefix: str, force=False) -> None:
    """Remove all objects in `bucket` whose keys begin with `prefix`.

    `prefix` must appear to be a directory -- that is, it must end with a slash.

    If you really mean to use `prefix='/'` -- which will wipe the entire bucket,
    up to 1,000 keys -- pass `force=True`. Otherwise, there is a safeguard
    against `prefix=''` specifically.
    """
    if not prefix.endswith("/"):
        raise ValueError("`prefix` must end with `/`")

    return _remove_by_prefix(bucket, prefix, force)


@contextmanager
def temporarily_download(
    bucket: str, key: str, dir=None
) -> ContextManager[pathlib.Path]:
    """Copy a file from S3 to a pathlib.Path; yield; and delete.

    Raise FileNotFoundError if the key is not on S3.

    Usage:

        with s3.temporarily_download('bucket', 'key') as path:
            print(str(path))  # a path on the filesystem
            path.read_bytes()  # returns file contents
        # when you exit the block, the pathlib.Path is deleted
    """
    with tempfile_context(prefix="s3-download-", dir=dir) as path:
        download(bucket, key, path)  # raise FileNotFoundError (deleting path)
        yield path


def download(bucket: str, key: str, path: pathlib.Path) -> None:
    """Copy a file from S3 to a pathlib.Path.

    Raise FileNotFoundError if the key is not on S3.
    """
    try:
        layer.downloader.download_file(bucket, key, str(path))
    # _downloader.download_file() seems to raise ClientError instead of a
    # wrapped error.
    # except layer.error.NoSuchKey:
    #     raise FileNotFoundError(errno.ENOENT, f'No file at {bucket}/{key}')
    except layer.error.ClientError as err:
        if err.response.get("Error", {}).get("Code") == "404":
            raise FileNotFoundError(errno.ENOENT, f"No file at {bucket}/{key}")
        else:
            raise
