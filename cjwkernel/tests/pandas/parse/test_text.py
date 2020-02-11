import io
import unittest

from cjwkernel.pandas.parse.text import detect_encoding


class DetectEncodingTest(unittest.TestCase):
    def test_detect_empty_is_ASCII(self):
        self.assertEqual(detect_encoding(io.BytesIO()), "UTF-8")

    def test_ascii_is_utf8(self):
        self.assertEqual(detect_encoding(io.BytesIO(b"hi")), "UTF-8")

    def test_utf8_is_utf8(self):
        self.assertEqual(
            detect_encoding(io.BytesIO("mon café latté est brulé".encode("utf-8"))),
            "UTF-8",
        )

    def test_windows_1252(self):
        self.assertEqual(
            detect_encoding(
                io.BytesIO("mon café latté coûte 5€".encode("windows-1252"))
            ),
            "WINDOWS-1252",
        )

    def test_utf16le(self):
        self.assertEqual(
            detect_encoding(
                io.BytesIO(b"\xff\xfe" + "j’aime le café, même à 5€".encode("utf-16le"))
            ),
            # NOT "UTF-16LE"
            # https://github.com/freedesktop/uchardet/commit/e5234d6b6181bb3bd022c2a67064a290011d9c14
            "UTF-16",
        )

    def test_utf16be(self):
        self.assertEqual(
            detect_encoding(
                io.BytesIO(b"\xfe\xff" + "j’aime le café, même à 5€".encode("utf-16be"))
            ),
            # NOT "UTF-16BE"
            # https://github.com/freedesktop/uchardet/commit/e5234d6b6181bb3bd022c2a67064a290011d9c14
            "UTF-16",
        )
