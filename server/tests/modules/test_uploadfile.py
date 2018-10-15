import unittest
import pandas as pd
from server.modules.uploadfile import UploadFile
from server.modules.types import ProcessResult
from .util import MockParams


mock_csv = 'A,B\n1,2\n2,3'


def render(has_header, table, fetch_result):
    x = UploadFile.render(MockParams(has_header=has_header), table,
                          fetch_result=fetch_result)
    result = ProcessResult.coerce(x)
    result.sanitize_in_place()
    return result


# This does not test the upload and parsing path, specifically
# UploadedFile.upload_to_table.
# See UploadFileViewTests for that
class UploadFileTests(unittest.TestCase):
    def test_no_file(self):
        result = render(True, None, None)
        self.assertEqual(result, ProcessResult())

    def test_has_header_true(self):
        result = render(True, None, ProcessResult(pd.DataFrame({'A': [1]})))
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1]})))

    def test_has_header_false(self):
        result = render(False, None, ProcessResult(pd.DataFrame({'A': [1]})))
        self.assertEqual(result,
                         ProcessResult(pd.DataFrame({'0': ['A', '1']})))

    def test_file_error(self):
        result = render(False, None, ProcessResult(error='x'))
        self.assertEqual(result, ProcessResult(error='x'))
