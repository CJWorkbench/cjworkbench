from contextlib import contextmanager
import errno
import hmac
import hashlib
import io
import math
import pathlib
import tempfile
from django.conf import settings
from minio import Minio
from minio import error  # noqa: F401 -- users may import it
from minio.error import ResponseError  # noqa: F401 -- users may import it
from urllib3.response import HTTPResponse

# https://localhost:9000/ => [ https:, localhost:9000 ]
_protocol, _unused, _endpoint = settings.MINIO_URL.split('/')

minio_client = Minio(_endpoint, access_key=settings.MINIO_ACCESS_KEY,
                     secret_key=settings.MINIO_SECRET_KEY,
                     secure=(_protocol == 'https:'))


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
    # have permission to run `minio_client.make_bucket()`
    if minio_client.bucket_exists(bucket_name):
        return

    # 2. Bucket doesn't exist, so attempt to create it
    try:
        minio_client.make_bucket(bucket_name)
    except ResponseError as err:
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
    response = minio_client.get_object(bucket, key)
    try:
        yield response
    finally:
        response.release_conn()


def list_file_keys(bucket: str, prefix: str):
    """
    List keys of non-directory objects, non-recursively, in `prefix`.

    >>> minio.list_file_keys('bucket', 'filter/a132b3f/')
    ['filter/a132b3f/spec.json', 'filter/a132b3f/filter.py']
    """
    objects = minio_client.list_objects_v2(bucket, prefix)
    return [o.object_name for o in objects
            if not o.is_dir]


def fput_directory_contents(bucket: str, prefix: str,
                            dirpath: pathlib.Path) -> None:
    if not prefix.endswith('/'):
        prefix = prefix + '/'

    paths = dirpath.glob('**/*')
    file_paths = [p for p in paths if p.is_file()]
    for file_path in file_paths:
        minio_client.fput_object(
            bucket_name=bucket,
            object_name=prefix + str(file_path.relative_to(dirpath)),
            file_path=str(file_path.resolve())
        )


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

    objects = minio_client.list_objects_v2(bucket, prefix, recursive=True)
    keys = [o.object_name for o in objects if not o.is_dir]
    if not keys:
        return
    for err in minio_client.remove_objects(bucket, keys):
        raise Exception('Error %s removing %s: %s' % (err.error_code,
                                                      err.object_name,
                                                      err.error_message))


@contextmanager
def temporarily_download(bucket: str, key: str) -> None:
    """
    Open a file on S3 as a NamedTemporaryFile.

    Usage:

        with minio.temporarily_download('bucket', 'key') as tf:
            print(repr(tf.name))  # a path on the filesystem
            tf.read()
    """
    with FullReadMinioFile(bucket, key) as tf:
        yield tf


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

        response = self._request_block(0)

        self.size = int(response.headers['Content-Range'].split('/')[1])
        self.tempfile = tempfile.TemporaryFile(prefix='RandomReadMinioFile')
        self.tempfile.truncate(self.size)  # allocate disk space
        nblocks = math.ceil(self.size / self.block_size)
        self.fetched_blocks = [False] * nblocks

        # Write first block
        block = response.read()
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

    def read(self, size):
        ret = super().read(size)
        return ret

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

    def _request_block(self, block_number: int) -> HTTPResponse:
        offset = block_number * self.block_size
        try:
            return minio_client.get_partial_object(self.bucket, self.key,
                                                   offset=offset,
                                                   length=self.block_size)
        except error.NoSuchKey:
            raise FileNotFoundError(
                errno.ENOENT,
                f'No file at {self.bucket}/{self.key}'
            )

    def _ensure_block_fetched(self, block_number: int) -> None:
        if self.fetched_blocks[block_number]:
            return

        # cache `pos`, write the block, then restore `pos`
        pos = self.tempfile.tell()
        response = self._request_block(block_number)
        self.tempfile.seek(block_number * self.block_size)
        self.tempfile.write(response.read())
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

        self.tempfile = tempfile.NamedTemporaryFile(prefix='FullReadMinioFile')
        self.name = self.tempfile.name
        try:
            minio_client.fget_object(self.bucket, self.key, self.tempfile.name)
        except error.NoSuchKey:
            raise FileNotFoundError(
                errno.ENOENT,
                f'No file at {self.bucket}/{self.key}'
            )

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
    def writable():
        return False

    # override io.RawIOBase
    def readinto(self, b: bytes) -> int:
        return self.tempfile.readinto(b)
