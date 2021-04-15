import contextlib
import unittest

from cjwmodule.arrow.testing import make_column, make_table
import cjwparquet

from cjwkernel.types import FetchResult, RenderError, I18nMessage
from cjwkernel.util import tempfile_context
from fetcher.versions import are_fetch_results_equal


class DiffTest(unittest.TestCase):
    def setUp(self):
        self.ctx = contextlib.ExitStack()
        self.old_path = self.ctx.enter_context(tempfile_context("diff-path1-"))
        self.new_path = self.ctx.enter_context(tempfile_context("diff-path2-"))

    def tearDown(self):
        self.ctx.close()

    def test_different_errors(self):
        self.assertFalse(
            are_fetch_results_equal(
                FetchResult(self.old_path, [RenderError(I18nMessage("foo", {}, None))]),
                FetchResult(self.old_path, [RenderError(I18nMessage("bar", {}, None))]),
            )
        )

    def test_old_parquet_new_empty(self):
        cjwparquet.write(self.old_path, make_table(make_column("A", [1])))
        self.assertFalse(
            are_fetch_results_equal(
                FetchResult(self.old_path), FetchResult(self.new_path)
            )
        )

    def test_new_parquet_old_empty(self):
        cjwparquet.write(self.old_path, make_table(make_column("A", [1])))
        self.assertFalse(
            are_fetch_results_equal(
                FetchResult(self.old_path), FetchResult(self.new_path)
            )
        )

    def test_parquet_different(self):
        cjwparquet.write(self.old_path, make_table(make_column("A", [1])))
        cjwparquet.write(self.new_path, make_table(make_column("A", [2])))
        self.assertFalse(
            are_fetch_results_equal(
                FetchResult(self.old_path), FetchResult(self.new_path)
            )
        )

    def test_parquet_same_data_different_bytes(self):
        cjwparquet.write(self.old_path, make_table(make_column("A", ["a"])))
        cjwparquet.write(
            self.new_path, make_table(make_column("A", ["a"], dictionary=True))
        )
        self.assertTrue(
            are_fetch_results_equal(
                FetchResult(self.old_path), FetchResult(self.new_path)
            )
        )

    def test_parquet_vs_non_parquet(self):
        cjwparquet.write(self.old_path, make_table(make_column("A", ["a"])))
        self.new_path.write_bytes(b"12345")
        self.assertFalse(
            are_fetch_results_equal(
                FetchResult(self.old_path), FetchResult(self.new_path)
            )
        )

    def test_bytes_different(self):
        self.old_path.write_bytes(b"slakdjhgt34kj5hlekretjhse3lk4j5ho234kj5rthsadf")
        self.new_path.write_bytes(b"salkdfhgbo324iu5q34rlkiuw3e47ytedasdfgaksjhg3r")
        self.assertFalse(
            are_fetch_results_equal(
                FetchResult(self.old_path), FetchResult(self.new_path)
            )
        )

    def test_bytes_same(self):
        self.old_path.write_bytes(b"12304987kljnmfe092394hkljdfs")
        self.new_path.write_bytes(b"12304987kljnmfe092394hkljdfs")
        self.assertTrue(
            are_fetch_results_equal(
                FetchResult(self.old_path), FetchResult(self.new_path)
            )
        )
