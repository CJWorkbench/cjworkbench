import asyncio
from collections import namedtuple
from contextlib import contextmanager
import io
import os.path
import unittest
from unittest.mock import patch
from asgiref.sync import async_to_sync
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import ProcessResult
from server.models import UploadedFile
from server.modules import uploadfile
from server.tests.utils import mock_xlsx_path


class FakeMinioObject(io.BytesIO):
    def release_conn(self):
        pass


FakeMinioStat = namedtuple('FakeMinioStat', ['size'])


mock_csv = 'A,B\n1,2\n2,3'
future_none = asyncio.Future()
future_none.set_result(None)


Csv = """A,B
1,fôo
2,bar""".encode('utf-8')


def render(has_header, fetch_result):
    return uploadfile.render(pd.DataFrame(), {'has_header': has_header},
                             fetch_result=fetch_result)


# See UploadFileViewTests for that
class UploadFileTests(unittest.TestCase):
    def test_render_no_file(self):
        result = render(True, None)
        assert_frame_equal(result, pd.DataFrame())

    def test_render_has_header_true(self):
        result = render(True, ProcessResult(pd.DataFrame({'A': [1]})))
        assert_frame_equal(result, pd.DataFrame({'A': [1]}))

    def test_render_has_header_false(self):
        result = render(False, ProcessResult(pd.DataFrame({'A': [1]})))
        assert_frame_equal(result, pd.DataFrame({'0': ['A', '1']}))

    def test_render_file_error(self):
        result = render(False, ProcessResult(error='x'))
        self.assertEqual(result, 'x')

    def _test_upload(self, *, uuid, filename, ext, size,
                     expected_result):
        uploaded_file = UploadedFile(
            uuid=uuid,
            name=filename,
            key=f'{uuid}.{ext}',
            bucket='our-bucket',
            size=size,
        )

        result = async_to_sync(uploadfile.parse_uploaded_file)(uploaded_file)
        # Assert frames are equal. Empty frames might differ in shape; ignore
        # that.
        self.assertEqual(result.dataframe.empty,
                         expected_result.dataframe.empty)
        if not result.dataframe.empty:
            assert_frame_equal(result.dataframe, expected_result.dataframe)

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
    def test_upload_xls(self, stat, s3_open):
        filename = os.path.join(os.path.dirname(__file__), '..', 'test_data',
                                'example.xls')
        with open(filename, 'rb') as file:
            file.release_conn = lambda: None
            s3_open.return_value = file
            stat.return_value = os.stat(filename)

            expected_table = pd.DataFrame({
                'foo': [1, 2],
                'bar': [2, 3],
            })

            self._test_upload(
                uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
                filename='test.xls',
                ext='xls',
                size=os.stat(filename).st_size,
                expected_result=ProcessResult(expected_table)
            )
            s3_open.assert_called_with(
                'our-bucket',
                'eb785452-f0f2-4ebe-97ce-e225e346148e.xls'
            )

    def test_invalid_mime_type(self):
        self._test_upload(
            uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
            filename='test.bin',
            ext='bin',
            size=3,
            expected_result=ProcessResult(error=(
                'Error parsing test.bin: unknown content type'
            ))
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
                'Error reading Excel file: Unsupported format, '
                "or corrupt file: Expected BOF record; found b'not an x'"
            ))
        )
