from base64 import b64encode
import hashlib
import io
import unittest
from unittest.mock import patch
from botocore.response import StreamingBody
from django.conf import settings
from urllib3.exceptions import ProtocolError
from cjwstate import minio


Bucket = minio.CachedRenderResultsBucket
Key = "key"
_original_streaming_read = StreamingBody.read


def _base64_md5sum(b: bytes) -> str:
    h = hashlib.md5()
    h.update(b)
    md5sum = h.digest()
    return b64encode(md5sum).decode("ascii")


def _clear() -> None:
    try:
        minio.remove(Bucket, Key)
    except minio.error.NoSuchKey:
        pass


def _put(b: bytes) -> None:
    minio.put_bytes(Bucket, Key, b)


class _MinioTest(unittest.TestCase):
    """
    Start and end each test with `Bucket` a valid, empty bucket.
    """

    def setUp(self):
        minio.ensure_bucket_exists(Bucket)
        _clear()

    def tearDown(self):
        _clear()


class TemporarilyDownloadTest(_MinioTest):
    def test_allows_reading_file(self):
        _put(b"1234")
        with minio.temporarily_download(Bucket, Key) as path:
            self.assertEqual(path.read_bytes(), b"1234")

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            with minio.temporarily_download(Bucket, Key) as _:
                pass


class UploadTest(_MinioTest):
    """
    Test that we help a _client_ upload files directly to minio.

    In these tests, the client is `urllib3`. It receives responses (including
    "ETag" header) directly from minio. We're testing that the URLs and headers
    are generated with the correct signature.
    """

    def _assume_role_session_client_with_write_access(self, bucket, key):
        credentials = minio.assume_role_to_write(bucket, key)
        # Import _after_ we've imported minio -- so cjwstate.minio's monkey-patch
        # takes effect.
        import boto3

        session = boto3.session.Session(
            aws_access_key_id=credentials["accessKeyId"],
            aws_secret_access_key=credentials["secretAccessKey"],
            aws_session_token=credentials["sessionToken"],
        )
        client = session.client("s3", endpoint_url=settings.MINIO_URL)
        return client

    def test_assume_role_to_write(self):
        client = self._assume_role_session_client_with_write_access(Bucket, "key")
        data = b"1234567"
        client.upload_fileobj(io.BytesIO(data), Bucket, "key")
        self.assertEqual(minio.get_object_with_data(Bucket, "key")["Body"], data)

    def test_assume_role_to_write_deny_wrong_key(self):
        client = self._assume_role_session_client_with_write_access(Bucket, "key1")
        data = b"1234567"
        with self.assertRaises(client.exceptions.ClientError):
            client.upload_fileobj(io.BytesIO(data), Bucket, "key")

    def test_assume_role_to_write_multipart(self):
        client = self._assume_role_session_client_with_write_access(Bucket, "key")
        from boto3.s3.transfer import TransferConfig

        data = b"1234567" * 1024 * 1024  # 7MB => 5MB+2MB parts
        client.upload_fileobj(
            io.BytesIO(data),
            Bucket,
            "key",
            Config=TransferConfig(multipart_threshold=5 * 1024 * 1024),
        )
        self.assertEqual(minio.get_object_with_data(Bucket, "key")["Body"], data)
