from base64 import b64encode
from contextlib import contextmanager
from dataclasses import dataclass
from email.utils import formatdate
import errno
import hmac
import hashlib
import io
import logging
import math
import pathlib
import tempfile
from typing import Any, Dict, List, Tuple
import urllib.parse
import urllib3
from django.conf import settings


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


def _build_content_disposition(filename: str) -> str:
    """
    Build a Content-Disposition header value for the given filename.
    """
    enc_filename = urllib.parse.quote(filename, encoding="utf-8")
    return "attachment; filename*=UTF-8''" + enc_filename


session = boto3.session.Session(
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
)
client = session.client(
    "s3", endpoint_url=settings.MINIO_URL  # e.g., 'https://localhost:9001/'
)
# Create the one transfer manager we'll reuse for all transfers. Otherwise,
# boto3 default is to create a transfer manager _per upload/download_, which
# means 10 threads per operation. (Primer: upload/download split over multiple
# threads to speed up transfer of large files.)
transfer_config = TransferConfig()
transfer = S3Transfer(client, transfer_config)
# boto3 exceptions are a bit odd -- https://github.com/boto/boto3/issues/1195
error = client.exceptions
"""
Namespace for exceptions.

Usage:

    from server import minio

    try:
        minio.client.head_bucket(Bucket='foo')
    except minio.error.NoSuchBucket as err:
        print(repr(err))
"""


def _build_bucket_name(key: str) -> str:
    return "".join(
        [settings.MINIO_BUCKET_PREFIX, "-", key, settings.MINIO_BUCKET_SUFFIX]
    )


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


def sign(b: bytes) -> bytes:
    """
    Build a signature of the given bytes.

    The return value proves we know our secret key.
    """
    return hmac.new(settings.MINIO_SECRET_KEY.encode("ascii"), b, hashlib.sha1).digest()


def list_file_keys(bucket: str, prefix: str):
    """
    List keys of non-directory objects, non-recursively, in `prefix`.

    >>> minio.list_file_keys('bucket', 'filter/a132b3f/')
    ['filter/a132b3f/spec.json', 'filter/a132b3f/filter.py']
    """
    response = client.list_objects_v2(
        Bucket=bucket, Prefix=prefix, Delimiter="/"  # avoid recursive
    )
    if "Contents" not in response:
        return []
    return [o["Key"] for o in response["Contents"]]


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


def create_multipart_upload(bucket: str, key: str, filename: str) -> str:
    """
    Initiate a multipart upload; return the upload ID.

    To add parts to the upload, call `upload_part()` with `bucket`, `key` and
    the returned `upload_id`.

    `filename` will be used to set a Content-Disposition header. We use this
    header to store the original filename in S3. The idea is, S3 stores _all_
    information about uploaded files.
    """
    response = client.create_multipart_upload(
        Bucket=bucket, Key=key, ContentDisposition=_build_content_disposition(filename)
    )
    return response["UploadId"]


def abort_multipart_upload(bucket: str, key: str, upload_id: str) -> None:
    """
    Abort the multipart upload, or raise `error.NoSuchUpload`.
    """
    client.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)


def _build_presigned_headers(
    http_method: str, resource: str, n_bytes: int, base64_md5sum: str
) -> Dict[str, str]:
    date = formatdate(timeval=None, localtime=False, usegmt=True)
    string_to_sign = "\n".join(
        [
            http_method,
            base64_md5sum,  # Content-MD5
            "",  # Content-Type -- we leave this blank
            "",  # we use 'x-amz-date', not 'Date'
            f"x-amz-date:{date}",
            resource,
        ]
    )
    signature = b64encode(sign(string_to_sign.encode("utf-8"))).decode("ascii")
    access_key = session.get_credentials().access_key
    return {
        "Authorization": f"AWS {access_key}:{signature}",
        "Content-Length": str(n_bytes),
        "Content-MD5": base64_md5sum,
        # no Content-Type
        "x-amz-date": date,  # Not 'Date': XMLHttpRequest disallows it
    }


def presign_upload(
    bucket: str, key: str, filename: str, n_bytes: int, base64_md5sum: str
) -> Tuple[str, Dict[str, str]]:
    """
    Return (url, headers) tuple for PUTting a file <5MB.

    The request is pre-signed: to use them you must PUT and you must not add or
    remove headers.
    """
    # https://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html
    resource = f"/{bucket}/{key}"
    url = settings.MINIO_EXTERNAL_URL + resource
    headers = _build_presigned_headers("PUT", resource, n_bytes, base64_md5sum)
    # Content-Disposition header doesn't affect the signature
    headers["Content-Disposition"] = _build_content_disposition(filename)
    return url, headers


def presign_upload_part(
    bucket: str,
    key: str,
    upload_id: str,
    part_number: int,
    n_bytes: int,
    base64_md5sum: str,
) -> Tuple[str, Dict[str, str]]:
    """
    Return (url, headers) tuple for PUTting a part.

    The request is pre-signed: to use them you must PUT and you must not add or
    remove headers.

    `part_number` starts at 1.
    """
    # https://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html
    resource = f"/{bucket}/{key}?partNumber={part_number}&uploadId={upload_id}"
    url = settings.MINIO_EXTERNAL_URL + resource
    headers = _build_presigned_headers("PUT", resource, n_bytes, base64_md5sum)
    return url, headers


def complete_multipart_upload(
    bucket: str, key: str, upload_id: str, etags: List[str]
) -> None:
    """
    Complete the multipart upload, or raise `error.NoSuchUpload`.

    `etags` must be a list of all ETags for all the parts uploaded, in part
    order.

    The total file size must be >5MB.
    """
    multipart_upload = {
        "Parts": [{"ETag": etag, "PartNumber": (i + 1)} for i, etag in enumerate(etags)]
    }
    return client.complete_multipart_upload(
        Bucket=bucket, Key=key, UploadId=upload_id, MultipartUpload=multipart_upload
    )


@dataclass
class Stat:
    size: int


def stat(bucket: str, key: str) -> Stat:
    """Return an object's metadata or raise an error."""
    response = client.head_object(Bucket=bucket, Key=key)
    return Stat(response["ContentLength"])


def fput_directory_contents(bucket: str, prefix: str, dirpath: pathlib.Path) -> None:
    if not prefix.endswith("/"):
        prefix = prefix + "/"

    paths = dirpath.glob("**/*")
    file_paths = [p for p in paths if p.is_file()]
    for file_path in file_paths:
        key = prefix + str(file_path.relative_to(dirpath))
        fput_file(bucket, key, file_path)


def remove(bucket: str, key: str) -> None:
    """Delete the file. No-op if it is already deleted."""
    try:
        client.delete_object(Bucket=bucket, Key=key)
    except error.NoSuchKey:
        pass


def copy(bucket: str, key: str, copy_source: str) -> None:
    client.copy_object(Bucket=bucket, Key=key, CopySource=copy_source)


def remove_recursive(bucket: str, prefix: str, force=False) -> None:
    """
    Remove all objects in `bucket` whose keys begin with `prefix`.

    If you really mean to use `prefix=''` -- which will wipe the entire bucket,
    up to 1,000 keys -- pass `force=True`. Otherwise, there is a safeguard
    against `prefix=''` specifically.
    """
    if not prefix.endswith("/"):
        raise ValueError("`prefix` must end with `/`")

    if prefix == "/" and not force:
        raise ValueError("Refusing to remove prefix=/ when force=False")

    # recursive list_objects_v2
    list_response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if "Contents" not in list_response:
        return
    delete_response = client.delete_objects(
        Bucket=bucket,
        Delete={"Objects": [{"Key": o["Key"]} for o in list_response["Contents"]]},
    )
    if "Errors" in delete_response:
        for err in delete_response["Errors"]:
            raise Exception("Error %{Code}s removing %{Key}s: %{Message}" % err)


def get_object_with_data(bucket: str, key: str, **kwargs) -> Dict[str, Any]:
    """
    Like client.get_object(), but response['Body'] is bytes.

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
def temporarily_download(bucket: str, key: str) -> None:
    """
    Copy a file from S3 to a pathlib.Path; yield; and delete.

    Raise FileNotFound if the key is not on S3.

    Usage:

        with minio.temporarily_download('bucket', 'key') as path:
            print(str(path))  # a path on the filesystem
            path.read_bytes()  # returns file contents
        # when you exit the block, the pathlib.Path is deleted
    """
    with tempfile.NamedTemporaryFile(prefix="minio_download") as tf:
        path = pathlib.Path(tf.name)
        download(bucket, key, path)  # raises FileNotFound
        yield path


def download(bucket: str, key: str, path: pathlib.Path) -> None:
    """
    Copy a file from S3 to a pathlib.Path.

    Raise FileNotFound if the key is not on S3.
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


class RandomReadMinioFile(io.RawIOBase):
    """
    A file on S3, cached in a tempfile.

    On init, an S3 query fills in `.size`, and `.tempfile` is created and set
    to the full file length.

    The file is fetched one `block_size`-sized block at a time. If you `seek()`
    you can skip fetching some blocks.

    If you intend to read the entire file, `FullReadMinioFile` will be more
    efficient.

    Usage:

        with RandomReadMinioFile(bucket, key) as file:
            file.read(10)  # read from start
            file.seek(-5, io.SEEK_END)
            file.read(5)  # read from end
    """

    def __init__(self, bucket: str, key: str, block_size=5 * 1024 * 1024):
        self.bucket = bucket
        self.key = key
        self.block_size = block_size

        response = self._request_block(0)
        self.size = int(response["ContentRange"].split("/")[1])
        self.tempfile = tempfile.TemporaryFile(prefix="RandomReadMinioFile")
        self.tempfile.truncate(self.size)  # allocate disk space
        nblocks = math.ceil(self.size / self.block_size)
        self.fetched_blocks = [False] * nblocks

        # Write first block
        self.tempfile.write(response["Body"])
        self.tempfile.seek(0, io.SEEK_SET)
        self.fetched_blocks[0] = True

    # override io.IOBase
    def tell(self) -> int:
        return self.tempfile.tell()

    # override io.IOBase
    def seek(self, offset: int, whence: int = 0) -> int:
        return self.tempfile.seek(offset, whence)

    # override io.IOBase
    def seekable(self):
        return True

    # override io.IOBase
    def close(self):
        self.tempfile.close()
        super().close()

    # override io.IOBase
    def readable(self):
        return True

    # override io.IOBase
    def writable(self):
        return False

    def read(self, size=-1):
        # TODO optimization: when size extends beyond our block (and in
        # particular, is -1), read all the blocks we need _in a single HTTP
        # request_ and then call super().read(size).
        return super().read(size)

    # override io.RawIOBase
    def readinto(self, b: bytes) -> int:
        pos = self.tempfile.tell()
        block_number = math.floor(pos / self.block_size)

        if block_number >= len(self.fetched_blocks):
            return 0

        self._ensure_block_fetched(block_number)

        pos_in_block = pos % self.block_size  # 0 <= x < self.block_size
        block_limit = self.block_size - pos_in_block
        limit = min(len(b), block_limit)
        nread = self.tempfile.readinto(memoryview(b)[:limit])
        return nread

    def _request_block(self, block_number: int) -> Dict[str, Any]:
        """
        Yield a boto3 dict with 'Body' (bytes) and 'ContentRange'.
        """
        offset = block_number * self.block_size
        http_range = f"bytes={offset}-{offset + self.block_size - 1}"
        try:
            return get_object_with_data(self.bucket, self.key, Range=http_range)
        except error.NoSuchKey:
            raise FileNotFoundError(
                errno.ENOENT, f"No file at {self.bucket}/{self.key}"
            )

    def _ensure_block_fetched(self, block_number: int) -> None:
        if self.fetched_blocks[block_number]:
            return

        response = self._request_block(block_number)

        # cache `pos`, write the block, then restore `pos`
        pos = self.tempfile.tell()
        self.tempfile.seek(block_number * self.block_size)
        self.tempfile.write(response["Body"])
        self.tempfile.seek(pos)

        self.fetched_blocks[block_number] = True


class FullReadMinioFile(io.RawIOBase):
    """
    A file on S3, cached in a tempfile.

    On init, the entire file is downloaded to `.tempfile`.

    If you intend to seek() and run logic that does not depend on the entire
    file contents, `RandomReadMinioFile` might suit your needs better.

    Usage:

        with FullReadMinioFile(bucket, key) as file:
            file.read(10)  # read from start
            file.seek(-5, io.SEEK_END)
            file.read(5)  # read from end
    """

    def __init__(self, bucket: str, key: str):
        self.bucket = bucket
        self.key = key

        with temporarily_download(bucket, key) as path:
            # POSIX-specific: reopen the file, then delete it from the
            # filesystem (by leaving the context manager).
            #
            # We'll use Python's default buffering settings.
            self.tempfile = path.open("rb")

    # override io.IOBase
    def tell(self) -> int:
        return self.tempfile.tell()

    # override io.IOBase
    def seek(self, offset: int, whence: int = 0) -> int:
        return self.tempfile.seek(offset, whence)

    # override io.IOBase
    def readable(self):
        return True

    # override io.IOBase
    def seekable(self):
        return True

    # override io.IOBase
    def close(self):
        self.tempfile.close()
        super().close()

    # override io.IOBase
    def writable():
        return False

    # override io.RawIOBase
    def readinto(self, b: bytes) -> int:
        return self.tempfile.readinto(b)
