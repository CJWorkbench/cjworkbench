from contextlib import contextmanager
from pathlib import Path
import unittest
from server import minio, parquet


bucket = minio.CachedRenderResultsBucket
key = 'key.par'
minio.ensure_bucket_exists(bucket)


class ParquetTest(unittest.TestCase):
    @contextmanager
    def _file_on_s3(self, relpath):
        path = Path(__file__).parent / 'test_data' / relpath
        try:
            minio.fput_file(bucket, key, path)
            yield
        finally:
            minio.remove(bucket, key)

    def test_read_header_issue_361(self):
        # https://github.com/dask/fastparquet/issues/361
        with self._file_on_s3('fastparquet-issue-361.par'):
            header = parquet.read_header(bucket, key)
            self.assertEqual(header.columns, [])
            self.assertEqual(header.count, 3)

    def test_read_issue_361(self):
        # https://github.com/dask/fastparquet/issues/361
        with self._file_on_s3('fastparquet-issue-361.par'):
            dataframe = parquet.read(bucket, key)
            self.assertEqual(list(dataframe.columns), [])
            self.assertEqual(len(dataframe), 3)

    def test_read_issue_375_uncompressed(self):
        with self._file_on_s3('fastparquet-issue-375.par'):
            with self.assertRaises(parquet.FastparquetIssue375):
                parquet.read(bucket, key)

    def test_read_issue_375_snappy(self):
        with self._file_on_s3('fastparquet-issue-375-snappy.par'):
            with self.assertRaises(parquet.FastparquetIssue375):
                parquet.read(bucket, key)
