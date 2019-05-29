from base64 import b64encode
import hashlib
import io
import unittest
from unittest.mock import patch
from botocore.response import StreamingBody
import urllib3
from urllib3.exceptions import ProtocolError
from server import minio


Bucket = minio.CachedRenderResultsBucket
Key = 'key'
_original_streaming_read = StreamingBody.read


def _base64_md5sum(b: bytes) -> str:
    h = hashlib.md5()
    h.update(b)
    md5sum = h.digest()
    return b64encode(md5sum).decode('ascii')


def _clear() -> None:
    try:
        minio.remove(Bucket, Key)
    except minio.error.NoSuchKey:
        pass


def _put(b: bytes) -> None:
    minio.put_bytes(Bucket, Key, b)


class _MinioTest(unittest.TestCase):
    """
    Start and end each test with `Bucket` a valid, empty bucket.
    """

    def setUp(self):
        minio.ensure_bucket_exists(Bucket)
        _clear()

    def tearDown(self):
        _clear()


class TemporarilyDownloadTest(_MinioTest):
    def test_allows_reading_file(self):
        _put(b'1234')
        with minio.temporarily_download(Bucket, Key) as path:
            self.assertEqual(path.read_bytes(), b'1234')

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            with minio.temporarily_download(Bucket, Key) as _:
                pass


class RandomReadMinioFileTest(_MinioTest):
    def test_raise_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            minio.RandomReadMinioFile(Bucket, Key)

    def test_raise_file_not_found_between_blocks(self):
        _put(b'123456')
        file = minio.RandomReadMinioFile(Bucket, Key, block_size=3)
        _clear()
        file.read(3)  # first block is already loaded
        with self.assertRaises(FileNotFoundError):
            file.read(3)  # second block can't be loaded

    def test_skip_block(self):
        _put(b'123456')
        file = minio.RandomReadMinioFile(Bucket, Key, block_size=2)
        file.read(2)  # read block #1
        file.seek(4)  # skip to block #3
        file.read(2)  # read block #3
        # At this point, block #2 shouldn't have been read. Test by deleting
        # the file before trying to read: the data shouldn't come through.
        _clear()
        file.seek(2)
        with self.assertRaises(Exception):
            file.read(2)  # this cannot possibly work

    def test_read_sequential(self):
        _put(b'123456')
        file = minio.RandomReadMinioFile(Bucket, Key, block_size=2)
        self.assertEqual(file.read(2), b'12')
        self.assertEqual(file.read(2), b'34')
        self.assertEqual(file.read(2), b'56')
        self.assertEqual(file.read(2), b'')

    def test_read_stops_at_block_boundary(self):
        # https://docs.python.org/3/library/io.html#io.RawIOBase:
        # Read up to size bytes from the object and return them. As a
        # convenience, if size is unspecified or -1, all bytes until EOF are
        # returned. Otherwise, only one system call is ever made. Fewer than
        # size bytes may be returned if the operating system call returns fewer
        # than size bytes.
        _put(b'123456')
        file = minio.RandomReadMinioFile(Bucket, Key, block_size=2)
        self.assertEqual(file.read(4), b'12')
        self.assertEqual(file.read(4), b'34')
        self.assertEqual(file.read(4), b'56')
        self.assertEqual(file.read(4), b'')

    def test_read_starting_mid_block(self):
        _put(b'123456')
        file = minio.RandomReadMinioFile(Bucket, Key, block_size=3)
        file.seek(2)
        self.assertEqual(file.read(2), b'3')

    def test_seek_to_end(self):
        _put(b'123456')
        file = minio.RandomReadMinioFile(Bucket, Key, block_size=3)
        file.seek(-2, io.SEEK_END)
        self.assertEqual(file.read(), b'56')

    def test_read_entire_file(self):
        _put(b'123456')
        file = minio.RandomReadMinioFile(Bucket, Key, block_size=2)
        file.seek(1)
        self.assertEqual(file.read(), b'23456')

    @patch.object(StreamingBody, 'read')
    def test_recover_after_read_protocolerror(self, read_mock):
        # Patch DownloadChunkIterator: first attempt to stream bytes raises
        # ProtocolError, but subsequent attempts succeed.
        #
        # We should retry after ProtocolError.
        read_mock.side_effect = [ProtocolError, b'123456']
        _put(b'123456')
        with self.assertLogs(minio.__name__, 'INFO') as logs:
            file = minio.RandomReadMinioFile(Bucket, Key)
            self.assertEqual(file.read(), b'123456')
            self.assertRegex(logs.output[0], 'Retrying exception')


class UploadTest(_MinioTest):
    """
    Test that we help a _client_ upload files directly to minio.

    In these tests, the client is `urllib3`. It receives responses (including
    "ETag" header) directly from minio. We're testing that the URLs and headers
    are generated with the correct signature.
    """

    def test_upload_empty_file(self):
        md5sum = _base64_md5sum(b'')
        url, headers = minio.presign_upload(Bucket, 'key', 't.csv', 0, md5sum)
        http = urllib3.PoolManager()
        response = http.request('PUT', url, body=b'', headers=headers)
        self.assertEqual(response.status, 200)
        self.assertEqual(minio.get_object_with_data(Bucket, 'key')['Body'],
                         b'')

    def test_upload_by_presigned_request(self):
        data = b'1234567'
        md5sum = _base64_md5sum(data)
        url, headers = minio.presign_upload(Bucket, 'key', 'file.csv',
                                            len(data), md5sum)
        http = urllib3.PoolManager()
        response = http.request('PUT', url, body=data, headers=headers)
        self.assertEqual(response.status, 200)
        self.assertEqual(minio.get_object_with_data(Bucket, 'key')['Body'],
                         data)
        head = minio.client.head_object(Bucket=Bucket, Key='key')
        self.assertEqual(head['ContentDisposition'],
                         "attachment; filename*=UTF-8''file.csv")

    def test_multipart_upload_by_presigned_requests(self):
        upload_id = minio.create_multipart_upload(Bucket, 'key', 'file.csv')
        data = b'1234567' * 1024 * 1024  # 7MB => 5MB+2MB parts
        data1 = data[:5*1024*1024]
        data2 = data[5*1024*1024:]
        md5sum1 = _base64_md5sum(data1)
        md5sum2 = _base64_md5sum(data2)
        url1, headers1 = minio.presign_upload_part(Bucket, 'key', upload_id,
                                                   1, len(data1), md5sum1)
        url2, headers2 = minio.presign_upload_part(Bucket, 'key', upload_id,
                                                   2, len(data2), md5sum2)
        http = urllib3.PoolManager()
        response1 = http.request('PUT', url1, body=data1, headers=headers1)
        self.assertEqual(response1.status, 200)
        etag1 = response1.headers['ETag'][1:-1]  # un-wrap quotes
        response2 = http.request('PUT', url2, body=data2, headers=headers2)
        self.assertEqual(response2.status, 200)
        etag2 = response2.headers['ETag'][1:-1]  # un-wrap quotes
        minio.complete_multipart_upload(Bucket, 'key', upload_id,
                                        [etag1, etag2])
        self.assertEqual(minio.get_object_with_data(Bucket, 'key')['Body'],
                         data)
