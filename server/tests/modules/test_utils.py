import asyncio
import io
import os.path
import unittest
from unittest.mock import patch
import numpy
import pandas as pd
from django.contrib.auth.models import User
from django.test import SimpleTestCase, override_settings
from pandas.testing import assert_frame_equal
from server.models import Workflow
from server.models.commands import InitWorkflowCommand
from server.modules.types import ProcessResult
from server.tests.utils import DbTestCase
from server.modules.utils import build_globals_for_eval, parse_bytesio, \
        turn_header_into_first_row, workflow_url_to_id, fetch_external_workflow


class SafeExecTest(unittest.TestCase):
    def exec_code(self, code):
        built_globals = build_globals_for_eval()
        inner_locals = {}
        exec(code, built_globals, inner_locals)
        return inner_locals

    def test_builtin_functions(self):
        env = self.exec_code("""
ret = sorted(list([1, 2, sum([3, 4])]))
""")
        self.assertEqual(env['ret'], [1, 2, 7])


class ParseBytesIoTest(SimpleTestCase):
    def test_parse_utf8_csv(self):
        result = parse_bytesio(io.BytesIO(b'A\ncaf\xc3\xa9'),
                               'text/csv', 'utf-8')
        expected = ProcessResult(
            pd.DataFrame({'A': ['café']}).astype('category')
        )
        self.assertEqual(result, expected)

    def test_replace_invalid_utf8(self):
        # \xe9 is ISO-8859-1 and we select 'utf-8' to test Workbench's recovery
        result = parse_bytesio(io.BytesIO(b'A\ncaf\xe9'),
                               'text/csv', 'utf-8')
        expected = ProcessResult(
            pd.DataFrame({'A': ['caf�']}).astype('category')
        )
        self.assertEqual(result, expected)

    def test_autodetect_charset_iso8859_1(self):
        # \xe9 is ISO-8859-1 so Workbench should auto-detect it
        result = parse_bytesio(io.BytesIO(b'A\ncaf\xe9'),
                               'text/csv', None)
        expected = ProcessResult(
            pd.DataFrame({'A': ['café']}).astype('category')
        )
        self.assertEqual(result, expected)

    def test_autodetect_charset_windows_1252(self):
        # \x96 is - in windows-1252, does not exist in UTF-8 or ISO-8859-1
        result = parse_bytesio(io.BytesIO(b'A\n2000\x962018'),
                               'text/csv', None)
        expected = ProcessResult(
            pd.DataFrame({'A': ['2000–2018']}).astype('category')
        )
        self.assertEqual(result, expected)

    def test_autodetect_charset_utf8(self):
        result = parse_bytesio(
            io.BytesIO(b'A\n\xE8\xB0\xA2\xE8\xB0\xA2\xE4\xBD\xA0'),
            'text/csv',
            None
        )
        expected = ProcessResult(
            pd.DataFrame({'A': ['谢谢你']}).astype('category')
        )
        self.assertEqual(result, expected)

    @override_settings(CHARDET_CHUNK_SIZE=3)
    def test_autodetect_charset_chunked(self):
        result = parse_bytesio(io.BytesIO(b'A\ncaf\xe9'),
                               'text/csv', None)
        expected = ProcessResult(
            pd.DataFrame({'A': ['café']}).astype('category')
        )
        self.assertEqual(result, expected)

    def test_json_with_nulls(self):
        result = parse_bytesio(io.BytesIO("""[
            {"A": "a"},
            {"A": null}
        ]""".encode('utf-8')), 'application/json')
        expected = ProcessResult(
            pd.DataFrame({'A': ['a', None]}, dtype=str)
        )
        self.assertEqual(result, expected)

    def test_json_with_undefined(self):
        result = parse_bytesio(io.BytesIO("""[
            {"A": "a"},
            {"A": "aa", "B": "b"}
        ]""".encode('utf-8')), 'application/json')
        expected = ProcessResult(
            pd.DataFrame({'A': ['a', 'aa'], 'B': [numpy.nan, 'b']}, dtype=str)
        )
        self.assertEqual(result, expected)

    def test_txt_detect_separator_semicolon(self):
        result = parse_bytesio(io.BytesIO(b'A;C\nB;D'),
                               'text/plain', 'utf-8')
        expected = ProcessResult(pd.DataFrame({'A': ['B'], 'C': ['D']}))
        self.assertEqual(result, expected)

    def test_txt_detect_separator_tab(self):
        result = parse_bytesio(io.BytesIO(b'A\tC\nB\tD'),
                               'text/plain', 'utf-8')
        expected = ProcessResult(pd.DataFrame({'A': ['B'], 'C': ['D']}))
        self.assertEqual(result, expected)

    def test_txt_detect_separator_comma(self):
        result = parse_bytesio(io.BytesIO(b'A,C\nB,D'),
                               'text/plain', 'utf-8')
        expected = ProcessResult(pd.DataFrame({'A': ['B'], 'C': ['D']}))
        self.assertEqual(result, expected)

    def test_csv_detect_separator_semicolon(self):
        result = parse_bytesio(io.BytesIO(b'A;C\nB;D'), 'text/csv', 'utf-8')
        expected = ProcessResult(pd.DataFrame({'A': ['B'], 'C': ['D']}))
        self.assertEqual(result, expected)

    def test_csv_no_na_filter(self):
        """
        We override pandas' urge to turn 'NA' into `np.nan`
        """
        result = parse_bytesio(io.BytesIO(b'A;C\nB;NA'), 'text/csv', 'utf-8')
        expected = ProcessResult(pd.DataFrame({'A': ['B'], 'C': ['NA']}))
        self.assertEqual(result, expected)

    def test_excel(self):
        with open(os.path.join(os.path.dirname(__file__), '..', 'test_data',
                               'example.xls'), 'rb') as file:
            result = parse_bytesio(file, 'application/vnd.ms-excel', None)
        expected = ProcessResult(
            pd.DataFrame({'foo': [1, 2], 'bar': [2, 3]})
        )
        self.assertEqual(result, expected)


class OtherUtilsTests(SimpleTestCase):
    def test_turn_header_into_first_row(self):
        result = turn_header_into_first_row(pd.DataFrame({'A': ['B'],
                                                          'C': ['D']}))
        expected = pd.DataFrame({'0': ['A', 'B'], '1': ['C', 'D']})
        assert_frame_equal(result, expected)

        # Function should return None when a table has not been uploaded yet
        self.assertIsNone(turn_header_into_first_row(None))

    def test_workflow_url_to_id(self):
        result_map = {
            'www.google.com': False,
            'https://app.workbenchdata.com/workflows/4370/': 4370,
            'https://staging.workbenchdata.com/workflows/18': 18,
            'not a url': False,
            'https://staging.workbenchdata.com/workflows/': False
        }

        for url, expected_result in result_map.items():
            if not expected_result:
                with self.assertRaises(Exception):
                    workflow_url_to_id(url)
            else:
                self.assertEqual(workflow_url_to_id(url), expected_result)


class FetchExternalWorkflowTest(DbTestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create(username='a', email='a@example.org')
        self.workflow = Workflow.objects.create(owner=self.user)
        self.tab = self.workflow.tabs.create(position=0)
        self.delta = InitWorkflowCommand.create(self.workflow)
        self.wf_module = self.tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=self.delta.id
        )

    def _fetch(self, *args):
        return self.run_with_async_db(fetch_external_workflow(*args))

    def test_workflow_access_denied(self):
        wrong_user = User(username='b', email='b@example.org')
        result = self._fetch(self.workflow.id + 1, wrong_user,
                             self.workflow.id)
        self.assertEqual(result, ProcessResult(
            error='Access denied to the target workflow'
        ))

    def test_deny_import_from_same_workflow(self):
        result = self._fetch(self.workflow.id, self.user, self.workflow.id)
        self.assertEqual(result, ProcessResult(
            error='Cannot import the current workflow'
        ))

    def test_workflow_does_not_exist(self):
        result = self._fetch(self.workflow.id + 1, self.user,
                             self.workflow.id + 2)
        self.assertEqual(result, ProcessResult(
            error='Target workflow does not exist'
        ))

    @patch('server.rabbitmq.queue_render')
    def test_workflow_has_no_cached_result(self, queue_render):
        future_none = asyncio.Future()
        future_none.set_result(None)
        queue_render.return_value = future_none

        result = self._fetch(self.workflow.id + 1, self.user, self.workflow.id)
        self.assertEqual(result, ProcessResult(
            error='Target workflow is rendering. Please try again.'
        ))
        queue_render.assert_called_with(self.workflow.id, self.delta.id)

    @patch('server.rabbitmq.queue_render')
    def test_workflow_has_wrong_cached_result(self, queue_render):
        future_none = asyncio.Future()
        future_none.set_result(None)
        queue_render.return_value = future_none

        self.wf_module.last_relevant_delta_id = self.delta.id - 1
        self.wf_module.cache_render_result(
            self.delta.id - 1,
            ProcessResult(pd.DataFrame({'A': [1]}))
        )
        self.wf_module.last_relevant_delta_id = self.delta.id
        self.wf_module.save(update_fields=['last_relevant_delta_id'])

        result = self._fetch(self.workflow.id + 1, self.user, self.workflow.id)
        self.assertEqual(result, ProcessResult(
            error='Target workflow is rendering. Please try again.'
        ))
        queue_render.assert_called_with(self.workflow.id, self.delta.id)

    def test_workflow_has_no_modules(self):
        self.wf_module.delete()
        result = self._fetch(self.workflow.id + 1, self.user, self.workflow.id)
        self.assertEqual(result, ProcessResult(
            error='Target workflow is empty'
        ))

    @patch('server.rabbitmq.queue_render')
    def test_happy_path(self, queue_render):
        self.wf_module.cache_render_result(
            self.delta.id,
            ProcessResult(pd.DataFrame({'A': [1]}))
        )
        self.wf_module.save()

        result = self._fetch(self.workflow.id + 1, self.user, self.workflow.id)
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1]})))
        queue_render.assert_not_called()
