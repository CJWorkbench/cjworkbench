from contextlib import contextmanager
import hmac
import hashlib
from django.conf import settings
from minio import Minio
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


def _ensure_user_files_bucket_exists():
    # 1. If bucket exists, return. This is good on production where we don't
    # have permission to run `minio_client.make_bucket()`
    if minio_client.bucket_exists(UserFilesBucket):
        return

    # 2. Bucket doesn't exist, so attempt to create it
    try:
        minio_client.make_bucket(UserFilesBucket)
    except ResponseError as err:
        raise RuntimeError(
            f'There is no bucket "{UserFilesBucket}" on the S3 server at '
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


_ensure_user_files_bucket_exists()
