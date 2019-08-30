import pandas as pd
import unittest
from pandas.testing import assert_frame_equal
from server.modules import upload
from cjwstate.tests.utils import MockPath


# See UploadFileViewTests for that
class UploadTest(unittest.TestCase):
    def test_render_no_file(self):
        result = upload.render(pd.DataFrame(), {"file": None, "has_header": True})
        assert_frame_equal(result, pd.DataFrame())

    def test_render_success(self):
        result = upload.render(
            pd.DataFrame(),
            {"file": MockPath(["x.csv"], b"A,B\na,b"), "has_header": True},
        )
        assert_frame_equal(result, pd.DataFrame({"A": ["a"], "B": ["b"]}))

    def test_render_error(self):
        result = upload.render(
            pd.DataFrame(), {"file": MockPath(["x.csv"], b""), "has_header": True}
        )
        self.assertEqual(result, "This file is empty")
