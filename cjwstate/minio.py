import errno
import json
import logging
import pathlib
import sys
import urllib3
import urllib.parse
from contextlib import contextmanager
from typing import Any, ContextManager, Dict, NamedTuple

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


session = boto3.session.Session(
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    region_name="us-east-1",
)
client = session.client(
    "s3",
    endpoint_url=settings.MINIO_URL,  # e.g., 'https://localhost:9001/'
    config=botocore.client.Config(max_pool_connections=50),
)

downloader = S3Transfer(client, TransferConfig())
"""Singleton S3 "downloader" for all downloads.

All concurrent downloads reuse the same thread pool. This caps the number of
threads S3 uses.
"""


uploader = S3Transfer(
    client, TransferConfig(use_threads=False, multipart_threshold=sys.maxsize)
)
"""Upload configuration.

To support Google Cloud Storage, we disable multipart uploads. Every upload
uses the calling thread and uploads in a single part.
"""

# boto3 exceptions are a bit odd -- https://github.com/boto/boto3/issues/1195
error = client.exceptions
"""Namespace for exceptions.

Usage:

    from cjwstate import minio

    try:
        minio.client.head_bucket(Bucket='foo')
    except minio.error.NoSuchBucket as err:
        print(repr(err))
"""


def _build_bucket_name(key: str) -> str:
    if settings.MINIO_BUCKET_PREFIX:
        # "production-user-files.workbenchdata.com" -- deprecated
        # (staging: "staging-user-files.workbenchdata.com")
        return "".join(
            [settings.MINIO_BUCKET_PREFIX, "-", key, settings.MINIO_BUCKET_SUFFIX]
        )
    else:
        # "user-files.workbenchdata.com" -- [2020-01-29] we want this everywhere
        # (staging: "user-files.workbenchdata-staging.com")
        return key + settings.MINIO_BUCKET_SUFFIX


UserFilesBucket = _build_bucket_name("user-files")
StaticFilesBucket = _build_bucket_name("static")
StoredObjectsBucket = _build_bucket_name("stored-objects")
ExternalModulesBucket = _build_bucket_name("external-modules")
CachedRenderResultsBucket = _build_bucket_name("cached-render-results")
TusUploadBucket = _build_bucket_name("upload")


def ensure_bucket_exists(bucket_name):
    # 1. If bucket exists, return. This is good on production where we don't
    # have permission to run `client.create_bucket()`
    try:
        client.head_bucket(Bucket=bucket_name)
        return
    except error.NoSuchBucket:
        pass
    except error.ClientError as err:
        # Botocore 1.12.130 seems to raise ClientError instead of NoSuchBucket
        if err.response["Error"]["Code"] != "404":
            raise

    # 2. Bucket doesn't exist, so attempt to create it
    try:
        client.create_bucket(Bucket=bucket_name)
    except error.AccessDenied as err:
        raise RuntimeError(
            f'There is no bucket "{bucket_name}" on the S3 server at '
            f'"{settings.MINIO_URL}", and we do not have permission to create '
            "it. Please create it manually and then restart Workbench.",
            cause=err,
        )


def list_file_keys(bucket: str, prefix: str):
    """List keys of non-directory objects, non-recursively, in `prefix`.

    >>> minio.list_file_keys('bucket', 'filter/a132b3f/')
    ['filter/a132b3f/spec.json', 'filter/a132b3f/filter.py']
    """
    # Use list_objects, not list_objects_v2, because Google Cloud Storage's
    # AWS emulation doesn't support v2.
    response = client.list_objects(
        Bucket=bucket, Prefix=prefix, Delimiter="/"  # avoid recursive
    )
    if response.get("IsTruncated"):
        # ... I guess we should paginate?
        raise NotImplementedError("list_objects() returned truncated result")
    return [o["Key"] for o in response.get("Contents", [])]


def fput_file(bucket: str, key: str, path: pathlib.Path) -> None:
    uploader.upload_file(str(path.resolve()), bucket, key)


def put_bytes(bucket: str, key: str, body: bytes, **kwargs) -> None:
    client.put_object(
        Bucket=bucket, Key=key, Body=body, ContentLength=len(body), **kwargs
    )


def exists(bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except error.NoSuchKey:
        return False
    except error.ClientError as err:
        # Botocore 1.12.130 seems to raise ClientError instead of NoSuchKey
        if err.response["Error"]["Code"] == "404":
            return False
        raise


class Stat(NamedTuple):
    size: int


def stat(bucket: str, key: str) -> Stat:
    """Return an object's metadata or raise an error."""
    response = client.head_object(Bucket=bucket, Key=key)
    return Stat(response["ContentLength"])


def remove(bucket: str, key: str) -> None:
    """Delete the file. No-op if it is already deleted."""
    try:
        client.delete_object(Bucket=bucket, Key=key)
    except error.NoSuchKey:
        pass


def copy(bucket: str, key: str, copy_source: str, **kwargs) -> None:
    client.copy_object(Bucket=bucket, Key=key, CopySource=copy_source, **kwargs)


def remove_by_prefix(bucket: str, prefix: str, force=False) -> None:
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
        list_response = client.list_objects(Bucket=bucket, Prefix=prefix)
        done = not list_response.get("IsTruncated", False)
        keys = [o["Key"] for o in list_response.get("Contents", [])]
        # Use client.delete_object(), not delete_objects(), because Google Cloud
        # Storage doesn't emulate DeleteObjects.
        #
        # This is slow. But so is multi-delete through minio, because minio's
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

    return remove_by_prefix(bucket, prefix, force)


def get_object_with_data(bucket: str, key: str, **kwargs) -> Dict[str, Any]:
    """Like client.get_object(), but response['Body'] is bytes.

    Why? Because if we're streaming it and we receive a urllib3.ProtocolError,
    there's no retry logic. Better to use the normal botocore retry logic.

    [adamhooper, 2019-04-22] I haven't found references online of anyone else
    doing this. Possibly we're receiving more ProtocolError than most because
    we're using minio. But I've seen plenty of similar errors with official S3,
    so I suspect this is a pattern many people might want to replicate.

    [adamhooper, 2019-04-22] A better implementation would be to create a
    different `get_object()` that has 'Body'.streaming = False.
    """
    max_attempts = transfer_config.num_download_attempts
    for i in range(max_attempts):
        try:
            response = client.get_object(Bucket=bucket, Key=key, **kwargs)
            body = response["Body"]
            try:
                data = body.read()
            finally:
                body.close()
            return {**response, "Body": data}
        except s3transfer.utils.S3_RETRYABLE_DOWNLOAD_ERRORS as e:
            logger.info(
                "Retrying exception caught (%s), "
                "retrying request, (attempt %d / %d)",
                e,
                i,
                max_attempts,
                exc_info=True,
            )
            last_exception = e
            # ... and retry
    raise last_exception


@contextmanager
def temporarily_download(
    bucket: str, key: str, dir=None
) -> ContextManager[pathlib.Path]:
    """Copy a file from S3 to a pathlib.Path; yield; and delete.

    Raise FileNotFoundError if the key is not on S3.

    Usage:

        with minio.temporarily_download('bucket', 'key') as path:
            print(str(path))  # a path on the filesystem
            path.read_bytes()  # returns file contents
        # when you exit the block, the pathlib.Path is deleted
    """
    with tempfile_context(prefix="minio-download-", dir=dir) as path:
        download(bucket, key, path)  # raise FileNotFoundError (deleting path)
        yield path


def download(bucket: str, key: str, path: pathlib.Path) -> None:
    """Copy a file from S3 to a pathlib.Path.

    Raise FileNotFoundError if the key is not on S3.
    """
    try:
        downloader.download_file(bucket, key, str(path))
    # downloader.download_file() seems to raise ClientError instead of a
    # wrapped error.
    # except error.NoSuchKey:
    #     raise FileNotFoundError(errno.ENOENT, f'No file at {bucket}/{key}')
    except error.ClientError as err:
        if err.response.get("Error", {}).get("Code") == "404":
            raise FileNotFoundError(errno.ENOENT, f"No file at {bucket}/{key}")
        else:
            raise
