import aiohttp
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
from cjworkbench.types import ProcessResult
from server.models import Workflow
from server.models.commands import InitWorkflowCommand
from server.modules.utils import build_globals_for_eval, parse_bytesio, \
        turn_header_into_first_row, workflow_url_to_id, \
        fetch_external_workflow, spooled_data_from_url
from server.tests.utils import DbTestCase


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
        expected = pd.DataFrame({'A': ['café']}).astype('category')
        assert_frame_equal(result.dataframe, expected)

    def test_json_with_nulls(self):
        result = parse_bytesio(io.BytesIO("""[
            {"A": "a"},
            {"A": null}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'A': ['a', None]}, dtype=str)
        assert_frame_equal(result.dataframe, expected)

    def test_json_with_int_nulls(self):
        result = parse_bytesio(io.BytesIO("""[
            {"A": 1},
            {"A": null}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'A': [1.0, numpy.nan]})
        assert_frame_equal(result.dataframe, expected)

    def test_json_str_numbers_are_str(self):
        """JSON input data speficies whether we're String and Number."""
        result = parse_bytesio(io.BytesIO("""[
            {"A": "1"},
            {"A": "2"}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'A': ['1', '2']})
        assert_frame_equal(result.dataframe, expected)

    def test_json_int64(self):
        """Support int64 -- like Twitter IDs."""
        result = parse_bytesio(io.BytesIO("""[
            {"A": 1093943422262697985}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'A': [1093943422262697985]})
        assert_frame_equal(result.dataframe, expected)

    def test_json_mixed_types_are_str(self):
        """Support int64 -- like Twitter IDs."""
        result = parse_bytesio(io.BytesIO("""[
            {"A": 1},
            {"A": "2"}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'A': ['1', '2']})
        assert_frame_equal(result.dataframe, expected)

    def test_json_str_dates_are_str(self):
        """JSON does not support dates."""
        result = parse_bytesio(io.BytesIO("""[
            {"date": "2019-02-20"},
            {"date": "2019-02-21"}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'date': ['2019-02-20', '2019-02-21']})
        assert_frame_equal(result.dataframe, expected)

    def test_json_bools_become_str(self):
        """Workbench does not support booleans; use True/False."""
        # Support null, too -- don't overwrite it.
        result = parse_bytesio(io.BytesIO("""[
            {"A": true},
            {"A": false},
            {"A": null}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'A': ['True', 'False', numpy.nan]})
        assert_frame_equal(result.dataframe, expected)

    def test_object_becomes_str(self):
        result = parse_bytesio(io.BytesIO("""[
            {"A": {"foo":"bar"}}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'A': ["{'foo': 'bar'}"]})
        assert_frame_equal(result.dataframe, expected)

    def test_array_becomes_str(self):
        result = parse_bytesio(io.BytesIO("""[
            {"A": ["foo", "bar"]}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'A': ["['foo', 'bar']"]})
        assert_frame_equal(result.dataframe, expected)

    def test_json_with_undefined(self):
        result = parse_bytesio(io.BytesIO("""[
            {"A": "a"},
            {"A": "aa", "B": "b"}
        ]""".encode('utf-8')), 'application/json')
        expected = pd.DataFrame({'A': ['a', 'aa'], 'B': [numpy.nan, 'b']})
        assert_frame_equal(result.dataframe, expected)

    def test_json_not_records(self):
        result = parse_bytesio(io.BytesIO(b'{"meta":{"foo":"bar"},"data":[]}'),
                               'application/json')
        expected = ProcessResult(error=(
            'Workbench cannot import this JSON file. The JSON file must '
            'be an Array of Objects for Workbench to import it.'
        ))
        self.assertEqual(result, expected)

    def test_json_not_array(self):
        """Workbench requires Array of Object"""
        result = parse_bytesio(io.BytesIO(b'{"last_updated":"02/21/2019"}'),
                               'application/json')
        self.assertEqual(result, ProcessResult(error=(
            'Workbench cannot import this JSON file. The JSON file '
            'must be an Array of Objects for Workbench to import it.'
        )))

    def test_json_syntax_error(self):
        result = parse_bytesio(io.BytesIO(b'{not JSON'), 'application/json')
        expected = ProcessResult(error=(
            'Invalid JSON (Unexpected character found when '
            "decoding 'null')"
        ))
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


class SpooledDataFromUrlTest(DbTestCase):
    def test_relative_url_raises_invalid_url(self):
        async def inner():
            async with spooled_data_from_url('/foo'):
                pass

        with self.assertRaises(aiohttp.InvalidURL):
            self.run_with_async_db(inner())

    def test_schemaless_url_raises_invalid_url(self):
        async def inner():
            async with spooled_data_from_url('//a/b'):
                pass

        with self.assertRaises(aiohttp.InvalidURL):
            self.run_with_async_db(inner())

    def test_mailto_url_raises_invalid_url(self):
        async def inner():
            async with spooled_data_from_url('mailto:user@example.org'):
                pass

        with self.assertRaises(aiohttp.InvalidURL):
            self.run_with_async_db(inner())


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
