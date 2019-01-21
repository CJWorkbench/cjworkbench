from contextlib import contextmanager
import hmac
import hashlib
import pathlib
import tempfile
from django.conf import settings
from minio import Minio
from minio import error  # noqa: F401 -- users may import it
from minio.error import ResponseError  # noqa: F401 -- users may import it

# https://localhost:9000/ => [ https:, localhost:9000 ]
_protocol, _unused, _endpoint = settings.MINIO_URL.split('/')

minio_client = Minio(_endpoint, access_key=settings.MINIO_ACCESS_KEY,
                     secret_key=settings.MINIO_SECRET_KEY,
                     secure=(_protocol == 'https:'))

UserFilesBucket = ''.join([
    settings.MINIO_BUCKET_PREFIX,
    '-',
    'user-files',
    settings.MINIO_BUCKET_SUFFIX
])


StaticFilesBucket = ''.join([
    settings.MINIO_BUCKET_PREFIX,
    '-',
    'static',
    settings.MINIO_BUCKET_SUFFIX
])


StoredObjectsBucket = ''.join([
    settings.MINIO_BUCKET_PREFIX,
    '-',
    'stored-objects',
    settings.MINIO_BUCKET_SUFFIX
])


ExternalModulesBucket = ''.join([
    settings.MINIO_BUCKET_PREFIX,
    '-',
    'external-modules',
    settings.MINIO_BUCKET_SUFFIX
])


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
    keys = (o.object_name for o in objects if not o.is_dir)
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
    with tempfile.NamedTemporaryFile() as tf:
        minio_client.fget_object(bucket, key, tf.name)
        yield tf
