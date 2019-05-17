import asyncio
from collections import namedtuple
from contextlib import contextmanager
import io
from pathlib import Path
from unittest.mock import patch
from asgiref.sync import async_to_sync
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import ProcessResult
from server import minio
from server.models import UploadedFile
from server.modules import uploadfile
from server.tests.utils import mock_xlsx_path, DbTestCase


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
class UploadFileTests(DbTestCase):  # DbTestCase clears minio
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
            bucket=minio.UserFilesBucket,
            size=size,
        )

        result = async_to_sync(uploadfile.parse_uploaded_file)(uploaded_file)
        # Assert frames are equal. Empty frames might differ in shape; ignore
        # that.
        self.assertEqual(result.dataframe.empty,
                         expected_result.dataframe.empty)
        if not result.dataframe.empty:
            assert_frame_equal(result.dataframe, expected_result.dataframe)

    def test_upload_csv(self):
        # Path through chardet encoding detection
        minio.put_bytes(minio.UserFilesBucket,
                        'eb785452-f0f2-4ebe-97ce-e225e346148e.csv', Csv)
        csv_table = pd.DataFrame({'A': [1, 2], 'B': ['fôo', 'bar']})
        csv_table['B'] = csv_table['B'].astype('category')
        self._test_upload(
            uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
            filename='test.csv',
            ext='csv',
            size=len(Csv),
            expected_result=ProcessResult(csv_table)
        )

    def test_upload_xlsx(self):
        path = Path(mock_xlsx_path)
        minio.fput_file(minio.UserFilesBucket,
                        'eb785452-f0f2-4ebe-97ce-e225e346148e.xlsx', path)
        expected_table = pd.DataFrame({
            'Month': ['Jan', 'Feb'],
            'Amount': [10, 20]
        })
        self._test_upload(
            uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
            filename='test.xlsx',
            ext='xlsx',
            size=path.stat().st_size,
            expected_result=ProcessResult(expected_table)
        )

    def test_upload_xls(self):
        path = (Path(__file__).parent.parent / 'test_data' / 'example.xls')
        minio.fput_file(minio.UserFilesBucket,
                        'eb785452-f0f2-4ebe-97ce-e225e346148e.xls', path)
        expected_table = pd.DataFrame({
            'foo': [1, 2],
            'bar': [2, 3],
        })

        self._test_upload(
            uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
            filename='test.xls',
            ext='xls',
            size=path.stat().st_size,
            expected_result=ProcessResult(expected_table)
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

    def test_invalid_xlsx_gives_error(self):
        minio.put_bytes(minio.UserFilesBucket,
                        'eb785452-f0f2-4ebe-97ce-e225e346148e.xlsx',
                        b'not an xlsx')
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
