import errno
import json
import logging
import pathlib
import urllib3
import urllib.parse
from contextlib import contextmanager
from typing import Any, ContextManager, Dict, NamedTuple

from django.conf import settings

from cjwkernel.util import tempfile_context


# Monkey-patch s3transfer so it retries on ProtocolError. On production,
# minio-the-GCS-gateway tends to drop connections once in a while; we want to
# retry those.
#
# This monkey-patch has to come before _anything_ (including other parts of
# s3transfer) reads it. That means this "import s3transfer.utils" has to be the
# first time anywhere in the app we import boto3 or s3transfer.
import s3transfer.utils

s3transfer.utils.S3_RETRYABLE_DOWNLOAD_ERRORS = (
    *s3transfer.utils.S3_RETRYABLE_DOWNLOAD_ERRORS,
    urllib3.exceptions.ProtocolError,
)

import boto3  # _after_ our s3transfer.utils monkey-patch!
from boto3.s3.transfer import S3Transfer, TransferConfig  # _after_ patch!


# Monkey-patch for https://github.com/boto/boto3/issues/1341
# The patch is from https://github.com/boto/botocore/pull/1328 and
# [2019-04-17, adamhooper] it's unclear why it hasn't been applied.
#
# TODO nix when https://github.com/boto/botocore/pull/1328 is merged
import botocore  # just so we can monkey-patch it

_original_send_request = botocore.awsrequest.AWSConnection._send_request


def _send_request(self, method, url, body, headers, *args, **kwargs):
    if headers.get("Content-Length") == "0":
        headers.pop("Expect", None)
    return _original_send_request(self, method, url, body, headers, *args, **kwargs)


botocore.awsrequest.AWSConnection._send_request = _send_request


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
    "s3", endpoint_url=settings.MINIO_URL  # e.g., 'https://localhost:9001/'
)
sts_client = session.client("sts", endpoint_url=settings.MINIO_URL)
# Create the one transfer manager we'll reuse for all transfers. Otherwise,
# boto3 default is to create a transfer manager _per upload/download_, which
# means 10 threads per operation. (Primer: upload/download split over multiple
# threads to speed up transfer of large files.)
transfer_config = TransferConfig()
transfer = S3Transfer(client, transfer_config)
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
    transfer.upload_file(str(path.resolve()), bucket, key)


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


def assume_role_to_write(bucket: str, key: str, duration_seconds: int = 18000) -> str:
    """Build temporary S3 credentials to let an external client write bucket/key.

    Return a dict of secretAccessKey, sessionToken, expiration, accessKeyId.
    """
    response = sts_client.assume_role(
        RoleArn="minio-notused-notused",
        RoleSessionName="minio-notused-notused",
        DurationSeconds=duration_seconds,
        Policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:PutObject",
                            "s3:AbortMultipartUpload",
                            "s3:ListMultipartUploadParts",
                        ],
                        "Resource": [f"arn:aws:s3:::{bucket}/{key}"],
                        # Don't worry about uploads having the wrong ACL: [2019-07-23] minio
                        # does not support object ACLs.
                    }
                ],
            }
        ),
    )
    credentials = response["Credentials"]
    return {
        "accessKeyId": credentials["AccessKeyId"],
        "secretAccessKey": credentials["SecretAccessKey"],
        "sessionToken": credentials["SessionToken"],
        "expiration": credentials["Expiration"],
    }


def abort_multipart_uploads_by_prefix(bucket: str, prefix: str) -> None:
    """Abort all multipart upload to the given prefix.

    This costs an API request to list uploads, and then an API request per
    multipart upload.

    WARNING: since this is minio, "prefix" must be "key". minio will not list
    multiple uploads in a directory, for instance.
    """
    response = client.list_multipart_uploads(Bucket=bucket, Prefix=prefix)
    for upload in response.get("Uploads", []):
        key = upload["Key"]
        upload_id = upload["UploadId"]
        client.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)


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
    # production. (cjwstate.minio talks with the Minio server, which delegates
    # to S3, or to GCS over the GCS "interoperability" layer.)
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
        if keys:
            to_delete = {"Objects": [{"Key": k} for k in keys]}
            delete_response = client.delete_objects(Bucket=bucket, Delete=to_delete)
            errors = [
                e for e in delete_response.get("Errors", []) if e["Code"] != "NoSuchKey"
            ]
            if errors:
                raise NotImplementedError(
                    (
                        "%(n_errors)d errors removing %(n_keys)d objects. "
                        "First error, on key %(key)s: Code %(code)s: %(message)s"
                    )
                    % dict(
                        n_errors=len(errors),
                        n_keys=len(keys),
                        key=errors[0]["Key"],
                        code=errors[0]["Code"],
                        message=errors[0]["Message"],
                    )
                )


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
        transfer.download_file(bucket, key, str(path))
    # transfer.download_file() seems to raise ClientError instead of a
    # wrapped error.
    # except error.NoSuchKey:
    #     raise FileNotFoundError(errno.ENOENT, f'No file at {bucket}/{key}')
    except error.ClientError as err:
        if err.response.get("Error", {}).get("Code") == "404":
            raise FileNotFoundError(errno.ENOENT, f"No file at {bucket}/{key}")
        else:
            raise
