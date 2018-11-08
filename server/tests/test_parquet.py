import os.path
import unittest
from server import parquet


def _path(relpath):
    return os.path.join(os.path.dirname(__file__), 'test_data', relpath)


class ParquetTest(unittest.TestCase):
    def test_read_header_issue_361(self):
        with self.assertRaises(parquet.FastparquetIssue361):
            parquet.read_header(_path('fastparquet-issue-361.par'))

    def test_read_issue_361(self):
        with self.assertRaises(parquet.FastparquetIssue361):
            parquet.read(_path('fastparquet-issue-361.par'))

    def test_read_issue_375_uncompressed(self):
        with self.assertRaises(parquet.FastparquetIssue375):
            parquet.read(_path('fastparquet-issue-375.par'))

    def test_read_issue_375_snappy(self):
        with self.assertRaises(parquet.FastparquetIssue375):
            parquet.read(_path('fastparquet-issue-375-snappy.par'))
