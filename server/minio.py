from contextlib import closing, contextmanager
from dataclasses import dataclass
import errno
import hmac
import hashlib
import io
import math
import pathlib
import tempfile
import urllib3
from django.conf import settings
import boto3
from boto3.s3.transfer import S3Transfer
import botocore


_original_send_request = botocore.awsrequest.AWSConnection._send_request
def _send_request(self, method, url, body, headers, *args, **kwargs):
    # Monkey-patch for https://github.com/boto/boto3/issues/1341
    # The patch is from https://github.com/boto/botocore/pull/1328 and
    # [2019-04-17, adamhooper] it's unclear why it hasn't been applied.
    #
    # TODO nix when https://github.com/boto/botocore/pull/1328 is merged
    if headers.get('Content-Length') == '0':
        headers.pop('Expect', None)
    return _original_send_request(self, method, url, body, headers, *args,
                                  **kwargs)
botocore.awsrequest.AWSConnection._send_request = _send_request


# Monkey-patch s3transfer so it retries on ProtocolError. On production,
# minio-the-GCS-gateway tends to drop connections once in a while; we want to
# retry those.
import s3transfer
s3transfer.utils.S3_RETRYABLE_DOWNLOAD_ERRORS = (
    *s3transfer.utils.S3_RETRYABLE_DOWNLOAD_ERRORS,
    urllib3.exceptions.ProtocolError
)
# Aaaand s3transfer.download imports the old tuple, so let's replace that one
s3transfer.download.S3_RETRYABLE_DOWNLOAD_ERRORS = \
        s3transfer.utils.S3_RETRYABLE_DOWNLOAD_ERRORS
# So does s3transfer.processpool
import s3transfer.processpool
s3transfer.processpool.S3_RETRYABLE_DOWNLOAD_ERRORS = \
        s3transfer.utils.S3_RETRYABLE_DOWNLOAD_ERRORS


client = boto3.client(
    's3',
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    endpoint_url=settings.MINIO_URL  # e.g., 'https://localhost:9001/'
)
# Create the one transfer manager we'll reuse for all transfers. Otherwise,
# boto3 default is to create a transfer manager _per upload/download_, which
# means 10 threads per operation. (Primer: upload/download split over multiple
# threads to speed up transfer of large files.)
transfer = S3Transfer(client)
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
    return ''.join([
        settings.MINIO_BUCKET_PREFIX,
        '-',
        key,
        settings.MINIO_BUCKET_SUFFIX,
    ])


UserFilesBucket = _build_bucket_name('user-files')
StaticFilesBucket = _build_bucket_name('static')
StoredObjectsBucket = _build_bucket_name('stored-objects')
ExternalModulesBucket = _build_bucket_name('external-modules')
CachedRenderResultsBucket = _build_bucket_name('cached-render-results')


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
        if err.response['Error']['Code'] != '404':
            raise

    # 2. Bucket doesn't exist, so attempt to create it
    try:
        client.create_bucket(Bucket=bucket_name)
    except error.AccessDenied as err:
        raise RuntimeError(
            f'There is no bucket "{bucket_name}" on the S3 server at '
            f'"{settings.MINIO_URL}", and we do not have permission to create '
            'it. Please create it manually and then restart Workbench.',
            cause=err
        )


def sign(b: bytes) -> bytes:
    """
    Build a signature of the given bytes.

    The return value proves we know our secret key.
    """
    return hmac.new(settings.MINIO_SECRET_KEY.encode('ascii'),
                    b, hashlib.sha1).digest()


@contextmanager
def open_for_read(bucket: str, key: str):
    """
    Open a file on S3 for read like a file-like object.

    Usage:

        with minio.open_for_read('bucket', 'key') as f:
            f.read()
    """
    response = client.get_object(Bucket=bucket, Key=key)
    body = response['Body']  # StreamingBody
    with closing(body):
        yield body


def list_file_keys(bucket: str, prefix: str):
    """
    List keys of non-directory objects, non-recursively, in `prefix`.

    >>> minio.list_file_keys('bucket', 'filter/a132b3f/')
    ['filter/a132b3f/spec.json', 'filter/a132b3f/filter.py']
    """
    response = client.list_objects_v2(
        Bucket=bucket,
        Prefix=prefix,
        Delimiter='/'  # avoid recursive
    )
    if 'Contents' not in response:
        return []
    return [o['Key'] for o in response['Contents']]


def fput_file(bucket: str, key: str, path: pathlib.Path) -> None:
    transfer.upload_file(str(path.resolve()), bucket, key)


def put_bytes(bucket: str, key: str, body: bytes) -> None:
    client.put_object(Bucket=bucket, Key=key, Body=body,
                      ContentLength=len(body))


def exists(bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except error.NoSuchKey:
        return False
    except error.ClientError as err:
        # Botocore 1.12.130 seems to raise ClientError instead of NoSuchKey
        if err.response['Error']['Code'] == '404':
            return False
        raise


@dataclass
class Stat:
    size: int


def stat(bucket: str, key: str) -> Stat:
    """Return an object's metadata or raise an error."""
    response = client.head_object(Bucket=bucket, Key=key)
    return Stat(response['ContentLength'])


def fput_directory_contents(bucket: str, prefix: str,
                            dirpath: pathlib.Path) -> None:
    if not prefix.endswith('/'):
        prefix = prefix + '/'

    paths = dirpath.glob('**/*')
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
    if not prefix.endswith('/'):
        raise ValueError('`prefix` must end with `/`')

    if prefix == '/' and not force:
        raise ValueError('Refusing to remove prefix=/ when force=False')

    # recursive list_objects_v2
    list_response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if 'Contents' not in list_response:
        return
    delete_response = client.delete_objects(
        Bucket=bucket,
        Delete={'Objects': [{'Key': o['Key']}
                            for o in list_response['Contents']]}
    )
    if 'Errors' in delete_response:
        for err in delete_response['Errors']:
            raise Exception('Error %{Code}s removing %{Key}s: %{Message}'
                            % err)


@contextmanager
def temporarily_download(bucket: str, key: str) -> None:
    """
    Open a file on S3 as a NamedTemporaryFile.

    Usage:

        with minio.temporarily_download('bucket', 'key') as tf:
            print(repr(tf.name))  # a path on the filesystem
            tf.read()
    """
    with tempfile.NamedTemporaryFile(prefix='minio_download') as tf:
        transfer.download_file(bucket, key, tf.name)
        yield tf  # really, only tf.name is useful


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
    def __init__(self, bucket: str, key: str, block_size=5*1024*1024):
        self.bucket = bucket
        self.key = key
        self.block_size = block_size

        with self._request_block(0) as response:
            self.size = int(response['ContentRange'].split('/')[1])
            self.tempfile = tempfile.TemporaryFile(prefix='RandomReadMinioFile')
            self.tempfile.truncate(self.size)  # allocate disk space
            nblocks = math.ceil(self.size / self.block_size)
            self.fetched_blocks = [False] * nblocks

            # Write first block
            block = response['Body'].read()
            self.tempfile.write(block)
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

    @contextmanager
    def _request_block(self, block_number: int):
        """
        Yield a boto3 dict with 'Body' (StreamingBody) and 'ContentRange'.

        The 'Body' will be closed when you leave the context. Use its '.read()'
        method to grab its contents.
        """
        offset = block_number * self.block_size
        http_range = f'bytes={offset}-{offset + self.block_size - 1}'
        try:
            response = client.get_object(
                Bucket=self.bucket,
                Key=self.key,
                Range=http_range
            )
        except error.NoSuchKey:
            raise FileNotFoundError(
                errno.ENOENT,
                f'No file at {self.bucket}/{self.key}'
            )
        body = response['Body']
        with closing(body):
            yield response

    def _ensure_block_fetched(self, block_number: int) -> None:
        if self.fetched_blocks[block_number]:
            return

        # cache `pos`, write the block, then restore `pos`
        pos = self.tempfile.tell()
        with self._request_block(block_number) as response:
            self.tempfile.seek(block_number * self.block_size)
            self.tempfile.write(response['Body'].read())
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

        with tempfile.NamedTemporaryFile(prefix='FullReadMinioFile') as tf:
            try:
                transfer.download_file(self.bucket, self.key, tf.name)
            except error.NoSuchKey:
                raise FileNotFoundError(
                    errno.ENOENT,
                    f'No file at {self.bucket}/{self.key}'
                )

            # POSIX-specific: reopen the file, then delete it from the
            # filesystem
            self.tempfile = open(tf.name, 'rb')

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
