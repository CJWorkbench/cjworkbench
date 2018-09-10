from minio import Minio
from django.conf import settings

# https://localhost:9000/ => [ https:, localhost:9000 ]
_protocol, _unused, _endpoint = settings.MINIO_URL.split('/')

minio_client = Minio(_endpoint, access_key=settings.MINIO_ACCESS_KEY,
                     secret_key=settings.MINIO_SECRET_KEY,
                     secure=(_protocol == 'https:'))

UserFilesBucket = ''.join(
    settings.MINIO_BUCKET_PREFIX,
    '_',
    'user-files',
    settings.MINIO_BUCKET_SUFFIX
)
