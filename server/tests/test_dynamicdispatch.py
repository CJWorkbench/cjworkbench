import os
import re
import shutil
import unittest
from unittest import mock
from pandas import DataFrame
from server.dynamicdispatch import DynamicModule, load_module
from server.models import WfModule
from server.modules.types import ProcessResult


class MockWfModule:
    def __init__(self, params={}, stored_table=None, stored_error=''):
        self.params = params
        self.stored_table = stored_table
        self.last_table = None
        self.fetch_error = stored_error
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
        # set-up structure, i.e. a way for the file to exist in a location
        # where it can be loaded dynamically
        # copy files to where they would be if this were a real module, i.e. a
        # non-test module.
        destdir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            '..',
            'importedmodules',
            'imported'
        )
        if not os.path.isdir(destdir):
            os.makedirs(destdir)

        versiondir = os.path.join(destdir, 'abcdef')
        if os.path.isdir(versiondir):
            shutil.rmtree(versiondir)
        shutil.copytree(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'test_data',
            'imported'
        ), versiondir)

        self.module = DynamicModule('imported', 'abcdef')

    def tearDown(self):
        shutil.rmtree(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            '..',
            'importedmodules',
            'imported'
        ))
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
        self.mock_render(lambda x, y: 1 / 0)  # raise exception
        result = self.render(MockWfModule(), DataFrame())
        result.error = re.sub('at line \d+', 'at line N', result.error)
        self.assertEqual(result, ProcessResult(error=(
            'ZeroDivisionError: division by zero '
            'at line N '
            f'of {os.path.basename(__file__)}'
        )))

    def test_render_table(self):
        table = DataFrame({'a': ['b']})
        out = DataFrame({'b': ['c']})
        self.mock_render(lambda x, y: out)
        result = self.render(MockWfModule(), table)
        self.assertEqual(result, ProcessResult(out))

    def test_render_error(self):
        self.mock_render(lambda x, y: (None, 'error'))
        result = self.render(MockWfModule(), DataFrame())
        self.assertEqual(result, ProcessResult(error='error'))

    def test_render_arg_params(self):
        # Render error=repr(args) and test they appear
        self.mock_render(lambda x, y: ProcessResult(x, repr(y)))
        wf_module = MockWfModule({'a': 'b'})
        table = DataFrame()
        result = self.render(wf_module, table)

        self.assertEqual(result, ProcessResult(
            dataframe=table,
            error=repr({'a': 'b'})
        ))

    def test_render_truncate(self):
        with mock.patch('django.conf.settings.MAX_ROWS_PER_TABLE', 2):
            out = DataFrame({'a': [1, 2, 3]})
            self.mock_render(lambda x, y: ProcessResult(out))
            result = self.render(MockWfModule(), DataFrame())
            self.assertEqual(len(out), 2)  # truncated in-place
            self.assertEqual(result, ProcessResult(
                dataframe=out,
                error='Truncated output from 3 rows to 2'
            ))

    def test_render_truncate_add_warning_to_error(self):
        with mock.patch('django.conf.settings.MAX_ROWS_PER_TABLE', 2):
            out = DataFrame({'a': [1, 2, 3]})
            self.mock_render(lambda x, y: ProcessResult(out, 'error1'))
            result = self.render(MockWfModule(), DataFrame())
            self.assertEqual(
                result.error,
                'error1\nTruncated output from 3 rows to 2'
            )

    def test_render_sanitize_table(self):
        self.mock_render(lambda x, y: ProcessResult(DataFrame({'a': [['b']]})))
        result = self.render(MockWfModule(), DataFrame())
        # Test that non-string value was coerced to string with repr()
        self.assertEqual(result, ProcessResult(DataFrame({'a': ["['b']"]})))

    def test_render_default_passthrough(self):
        del self.module.module.render
        table = DataFrame({'a': [1]})
        result = self.render(MockWfModule(), table)
        self.assertEqual(result, ProcessResult(table))

    def test_render_default_cached(self):
        del self.module.module.render
        table1 = DataFrame({'a': [1]})
        table2 = DataFrame({'b': [2]})
        result = self.render(
            MockWfModule(stored_table=table2, stored_error=''),
            table1
        )
        self.assertEqual(result, ProcessResult(table2))

    def test_render_default_error(self):
        del self.module.module.render
        table = DataFrame()
        result = self.render(
            MockWfModule(stored_table=table, stored_error='Error'),
            table
        )
        self.assertEqual(result, ProcessResult(table, 'Error'))

    def fetch(self, wf_module):
        out_func = 'server.modules.moduleimpl.ModuleImpl.commit_result'
        with mock.patch(out_func) as m:
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
        self.assertIs(wf_module, args[0])
        result = args[1]
        result.error = re.sub('at line \d+', 'at line N', result.error)
        self.assertEqual(result, ProcessResult(error=(
            'ZeroDivisionError: division by zero at line N '
            f'of {os.path.basename(__file__)}'
        )))

    def test_fetch_passes_params(self):
        wf_module = MockWfModule({'a': 'b'})
        self.mock_fetch(lambda p: ProcessResult(error=repr(p)))
        m = self.fetch(wf_module)
        self.assertTrue(m.called)
        args = m.call_args[0]
        self.assertIs(args[0], wf_module)
        self.assertEqual(args[1], ProcessResult(error=repr({'a': 'b'})))

    def test_fetch_sends_data_frame(self):
        wf_module = MockWfModule()
        table = DataFrame()
        self.mock_fetch(lambda p: ProcessResult(table))
        m = self.fetch(wf_module)
        self.assertTrue(m.called)
        args = m.call_args[0]
        self.assertIs(args[0], wf_module)
        self.assertEqual(args[1], ProcessResult(table))
