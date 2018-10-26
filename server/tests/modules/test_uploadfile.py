import asyncio
from collections import namedtuple
from contextlib import contextmanager
import io
import unittest
from unittest.mock import patch
from asgiref.sync import async_to_sync
import pandas as pd
from pandas.testing import assert_frame_equal
from server.models import UploadedFile
from server.modules.uploadfile import UploadFile, upload_to_table
from server.modules.types import ProcessResult
from server.tests.utils import mock_xlsx_path
from .util import MockParams


class FakeMinioObject(io.BytesIO):
    def release_conn(self):
        pass


@contextmanager
def mock_file(b):
    with io.BytesIO(b) as bio:
        yield bio


FakeMinioStat = namedtuple('FakeMinioStat', ['size'])


mock_csv = 'A,B\n1,2\n2,3'
future_none = asyncio.Future()
future_none.set_result(None)


Csv = """A,B
1,fôo
2,bar""".encode('utf-8')


XlsxType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def render(has_header, table, fetch_result):
    x = UploadFile.render(MockParams(has_header=has_header), table,
                          fetch_result=fetch_result)
    result = ProcessResult.coerce(x)
    result.sanitize_in_place()
    return result


# See UploadFileViewTests for that
class UploadFileTests(unittest.TestCase):
    def test_render_no_file(self):
        result = render(True, None, None)
        self.assertEqual(result, ProcessResult())

    def test_render_has_header_true(self):
        result = render(True, None, ProcessResult(pd.DataFrame({'A': [1]})))
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1]})))

    def test_render_has_header_false(self):
        result = render(False, None, ProcessResult(pd.DataFrame({'A': [1]})))
        self.assertEqual(result,
                         ProcessResult(pd.DataFrame({'0': ['A', '1']})))

    def test_render_file_error(self):
        result = render(False, None, ProcessResult(error='x'))
        self.assertEqual(result, ProcessResult(error='x'))

    @patch('server.modules.moduleimpl.ModuleImpl.commit_result')
    def _test_upload(self, commit_result, *, uuid, filename, ext, size,
                     expected_result):
        commit_result.return_value = future_none

        wf_module = 'stub'
        uploaded_file = UploadedFile(
            uuid=uuid,
            name=filename,
            key=f'{uuid}.{ext}',
            bucket='our-bucket',
            size=size,
        )
        uploaded_file.delete = unittest.mock.Mock()

        async_to_sync(upload_to_table)(wf_module, uploaded_file)

        # Check commit_result was called
        commit_result.assert_called()
        result = commit_result.call_args[0][1]
        self.assertEqual(result.error, expected_result.error)
        # Assert frames are equal. Empty frames might differ in shape; ignore
        # that.
        self.assertEqual(result.dataframe.empty,
                         expected_result.dataframe.empty)
        if not result.dataframe.empty:
            assert_frame_equal(result.dataframe, expected_result.dataframe)

        # Assert we delete the file if we can't parse it.
        if expected_result.error:
            uploaded_file.delete.assert_called()

    @patch('minio.api.Minio.get_object')
    @patch('minio.api.Minio.stat_object')
    def test_upload_csv(self, stat, s3_open):
        # Path through chardet encoding detection
        s3_open.return_value = FakeMinioObject(Csv)
        stat.return_value = FakeMinioStat(len(Csv))

        csv_table = pd.DataFrame({'A': [1, 2], 'B': ['fôo', 'bar']})
        csv_table['B'] = csv_table['B'].astype('category')

        self._test_upload(
            uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
            filename='test.csv',
            ext='csv',
            size=len(Csv),
            expected_result=ProcessResult(csv_table)
        )
        s3_open.assert_called_with(
            'our-bucket',
            'eb785452-f0f2-4ebe-97ce-e225e346148e.csv'
        )

    @patch('minio.api.Minio.get_object')
    @patch('minio.api.Minio.stat_object')
    def test_upload_xlsx(self, stat, s3_open):
        with open(mock_xlsx_path, 'rb') as bio:
            b = bio.read()
        s3_open.return_value = FakeMinioObject(b)
        stat.return_value = FakeMinioStat(len(b))

        expected_table = pd.DataFrame({
            'Month': ['Jan', 'Feb'],
            'Amount': [10, 20]
        })

        self._test_upload(
            uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
            filename='test.xlsx',
            ext='xlsx',
            size=len(b),
            expected_result=ProcessResult(expected_table)
        )
        s3_open.assert_called_with(
            'our-bucket',
            'eb785452-f0f2-4ebe-97ce-e225e346148e.xlsx'
        )

    @patch('minio.api.Minio.get_object')
    @patch('minio.api.Minio.stat_object')
    @patch('minio.api.Minio.remove_object')
    def test_invalid_xlsx_gives_error(self, remove_object, stat_object,
                                      get_object):
        get_object.return_value = FakeMinioObject(b'not an xlsx')
        stat_object.return_value = FakeMinioStat(10)

        self._test_upload(
            uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
            filename='test.xlsx',
            ext='xlsx',
            size=len(b'not an xlsx'),
            expected_result=ProcessResult(error=(
                'Error reading Excel file: Unsupported format, or corrupt file: '
                "Expected BOF record; found b'not an x'"
            ))
        )
