import unittest

from cjwstate import minio

Bucket = minio.CachedRenderResultsBucket
Key = "key"


def _clear() -> None:
    minio.remove(Bucket, Key)


def _put(b: bytes) -> None:
    minio.put_bytes(Bucket, Key, b)


class TemporarilyDownloadTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        minio.ensure_bucket_exists(Bucket)
        _clear()

    def tearDown(self):
        _clear()
        super().tearDown()

    def test_allows_reading_file(self):
        _put(b"1234")
        with minio.temporarily_download(Bucket, Key) as path:
            self.assertEqual(path.read_bytes(), b"1234")

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            with minio.temporarily_download(Bucket, Key) as _:
                pass
