from unittest import mock

from ..models import WfModule
from ..dynamicdispatch import DynamicModule, load_module
import json, os, shutil, types
from pandas import DataFrame
import unittest


class MockWfModule:
    def __init__(self, params={}, stored_table=None, stored_error=''):
        self.params = params
        self.stored_table = stored_table
        self.last_table = None
        self.error_msg = stored_error
        self.status = WfModule.BUSY

        self.set_busy_calls = []


    def create_parameter_dict(self, table):
        self.last_table = table
        return self.params


    def retrieve_fetched_table(self):
        return self.stored_table


    def set_busy(self, **kwargs):
        self.set_busy_calls.append(kwargs)


class DynamicDispatchTest(unittest.TestCase):
    def setUp(self):
        # Extract module specification from test_data/imported.
        # This has the modified .py file that add_boilerplate_and_check_syntax() creates when it loads from github
        pwd = os.path.dirname(os.path.abspath(__file__))
        test_json = os.path.join(pwd, "test_data/imported", "imported.json")
        with open(test_json) as readable:
            module_config = json.load(readable)

        #set-up structure, i.e. a way for the file to exist in a location where it can be loaded dynamically
        #copy files to where they would be if this were a real module, i.e. a non-test module.
        destdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "importedmodules", "imported")
        if not os.path.isdir(destdir):
            os.makedirs(destdir)

        versiondir = os.path.join(destdir, "abcdef")
        if os.path.isdir(versiondir):
            shutil.rmtree(versiondir)
        shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data", "imported"), versiondir)

        self.module = DynamicModule('imported', 'abcdef')


    def tearDown(self):
        shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "importedmodules", "imported"))
        load_module.cache_clear()


    @property
    def render(self):
        return self.module.render


    def mock_render(self, func):
        self.module.module.render = func


    def test_load_is_cached(self):
        # if we call again, should be cached
        with mock.patch('os.listdir') as mocked:
            DynamicModule('imported', 'abcdef')
            self.assertEqual(mocked.call_count, 0)


    def test_render_none(self):
        self.assertEqual(self.render(MockWfModule(), None), None)


    def test_render_exception(self):
        self.mock_render(lambda x, y: 1 / 0) # raise exception
        ret = self.render(MockWfModule(), DataFrame())
        self.assertTrue(ret[0].empty)
        self.assertRegexpMatches(
            ret[1],
            f'ZeroDivisionError: .* at line \\d+ of {os.path.basename(__file__)}'
        )


    def test_render_table(self):
        table = DataFrame({ 'a': [ 'b' ] })
        out = DataFrame({ 'b': [ 'c' ] })
        self.mock_render(lambda x, y: out)
        ret = self.render(MockWfModule(), table)
        self.assertIs(ret[0], out)
        self.assertEqual(ret[1], '')


    def test_render_error(self):
        self.mock_render(lambda x, y: (None, 'error'))
        ret = self.render(MockWfModule(), DataFrame())
        self.assertEqual(ret[1], 'error')


    def test_render_arg_table(self):
        table = DataFrame({ 'a': [ 'b' ] })
        self.mock_render(lambda x, y: (x, None))
        ret = self.render(MockWfModule(), table)
        self.assertIs(ret[0], table)


    def test_render_arg_params(self):
        self.mock_render(lambda x, y: (x, repr(y)))
        wf_module = MockWfModule({ 'a': 'b' })
        table = DataFrame()
        ret = self.render(wf_module, table)

        # Assert wf_module.create_parameter_dict(table) was called
        self.assertIs(wf_module.last_table, table)

        # Assert its retval was passed to module's render()
        self.assertEqual(ret[1], repr({ 'a': 'b' }))


    def test_render_truncate(self):
        with mock.patch('django.conf.settings.MAX_ROWS_PER_TABLE', 2) as m:
            out = DataFrame({ 'a': [ 1, 2, 3 ] })
            self.mock_render(lambda x, y: out)
            ret = self.render(MockWfModule(), DataFrame())
            self.assertIs(ret[0], out) # was truncated in-place
            self.assertEqual(len(ret[0]), 2)
            self.assertEqual(ret[1], 'Truncated output from 3 rows to 2')


    def test_render_truncate_add_warning_to_error(self):
        with mock.patch('django.conf.settings.MAX_ROWS_PER_TABLE', 2) as m:
            out = DataFrame({ 'a': [ 1, 2, 3 ] })
            self.mock_render(lambda x, y: (out, 'error1'))
            ret = self.render(MockWfModule(), DataFrame())
            self.assertIs(ret[0], out) # was truncated in-place
            self.assertEqual(len(ret[0]), 2)
            self.assertEqual(ret[1], 'error1\nTruncated output from 3 rows to 2')


    def test_render_sanitize_table(self):
        self.mock_render(lambda x, y: DataFrame({ 'a': [{ 'b': 'c' }] }))
        ret = self.render(MockWfModule(), DataFrame())
        # Test that non-string value was coerced to string with repr()
        self.assertEqual(ret[0].at[0, 'a'], repr({ 'b': 'c' }))


    def test_render_default_passthrough(self):
        del self.module.module.render
        table = DataFrame()
        ret = self.render(MockWfModule(), table)
        self.assertIs(ret[0], table)


    def test_render_default_cached(self):
        del self.module.module.render
        table1 = DataFrame()
        table2 = DataFrame()
        ret = self.render(
            MockWfModule(stored_table=table2, stored_error=''),
            table1
        )
        self.assertIs(ret[0], table2)
        self.assertEqual(ret[1], '')


    def test_render_default_error(self):
        del self.module.module.render
        table = DataFrame()
        ret = self.render(
            MockWfModule(stored_table=table, stored_error='Error'),
            table
        )
        self.assertEqual(ret[1], 'Error')


    def fetch(self, wf_module):
        with mock.patch('server.versions.save_fetched_table_if_changed') as m:
            self.module.fetch(wf_module)
            return m


    def mock_fetch(self, func):
        self.module.module.fetch = func


    def test_fetch_default_nothing(self):
        # Really, we're testing that we don't get any errors
        wf_module = MockWfModule()
        m = self.fetch(wf_module)
        self.assertEqual(len(wf_module.set_busy_calls), 0)
        self.assertFalse(m.called)


    def test_fetch_wrap_exception(self):
        wf_module = MockWfModule()
        self.mock_fetch(lambda p: 1 / 0)
        m = self.fetch(wf_module)
        self.assertTrue(m.called)
        args = m.call_args[0]
        self.assertIs(args[0], wf_module)
        self.assertEqual(len(args[1]), 0)
        self.assertRegexpMatches(
            args[2],
            f'ZeroDivisionError: .* at line \\d+ of {os.path.basename(__file__)}'
        )


    def test_fetch_passes_params(self):
        wf_module = MockWfModule({ 'a': 'b' })
        self.mock_fetch(lambda p: (None, repr(p)))
        m = self.fetch(wf_module)
        self.assertTrue(m.called)
        args = m.call_args[0]
        self.assertIs(args[0], wf_module)
        args = m.call_args[0]
        self.assertEqual(args[2], repr({ 'a': 'b' }))


    def test_fetch_sends_data_frame(self):
        wf_module = MockWfModule()
        table = DataFrame()
        self.mock_fetch(lambda p: (table, None))
        m = self.fetch(wf_module)
        self.assertTrue(m.called)
        args = m.call_args[0]
        self.assertIs(args[0], wf_module)
        self.assertIs(args[1], table)
        self.assertEqual(args[2], '')
