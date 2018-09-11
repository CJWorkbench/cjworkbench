from contextlib import contextmanager
import hmac
import hashlib
from django.conf import settings
from minio import Minio
from minio.error import ResponseError  # for export

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
        print(repr(response))
        yield response
    finally:
        response.release_conn()
