from contextlib import contextmanager
import os.path
import unittest
from server import minio, parquet


bucket = minio.CachedRenderResultsBucket
key = 'key.par'
minio.ensure_bucket_exists(bucket)


class ParquetTest(unittest.TestCase):
    @contextmanager
    def _file_on_s3(self, relpath):
        path = os.path.join(os.path.dirname(__file__),
                            'test_data', relpath)
        try:
            minio.minio_client.fput_object(bucket, key, path)
            yield
        finally:
            minio.minio_client.remove_object(bucket, key)

    def test_read_header_issue_361(self):
        with self._file_on_s3('fastparquet-issue-361.par'):
            with self.assertRaises(parquet.FastparquetIssue361):
                parquet.read_header(bucket, key)

    def test_read_issue_361(self):
        with self._file_on_s3('fastparquet-issue-361.par'):
            with self.assertRaises(parquet.FastparquetIssue361):
                parquet.read(bucket, key)

    def test_read_issue_375_uncompressed(self):
        with self._file_on_s3('fastparquet-issue-375.par'):
            with self.assertRaises(parquet.FastparquetIssue375):
                parquet.read(bucket, key)

    def test_read_issue_375_snappy(self):
        with self._file_on_s3('fastparquet-issue-375-snappy.par'):
            with self.assertRaises(parquet.FastparquetIssue375):
                parquet.read(bucket, key)
