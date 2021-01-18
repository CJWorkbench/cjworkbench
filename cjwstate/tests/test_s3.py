import unittest

from cjwstate import s3

Bucket = s3.CachedRenderResultsBucket
Key = "key"


def _clear() -> None:
    s3.remove(Bucket, Key)


def _put(b: bytes) -> None:
    s3.put_bytes(Bucket, Key, b)


class TemporarilyDownloadTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        s3.ensure_bucket_exists(Bucket)
        _clear()

    def tearDown(self):
        _clear()
        super().tearDown()

    def test_allows_reading_file(self):
        _put(b"1234")
        with s3.temporarily_download(Bucket, Key) as path:
            self.assertEqual(path.read_bytes(), b"1234")

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            with s3.temporarily_download(Bucket, Key) as _:
                pass
