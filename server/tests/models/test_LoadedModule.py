import asyncio
from collections import namedtuple
import inspect
import logging
import os.path
import shutil
import tempfile
from unittest.mock import Mock, patch
from asgiref.sync import async_to_sync
from django.conf import settings
from django.test import SimpleTestCase, override_settings
import pandas as pd
from pandas.testing import assert_frame_equal
from server.models import LoadedModule
import server.models.loaded_module
from server.modules.types import ProcessResult
import server.modules.pastecsv
from server.tests.modules.util import MockParams
from server.models.param_field import ParamDTypeDict, ParamDTypeString, \
        ParamDTypeInteger, ParamDTypeBoolean


MockModuleVersion = namedtuple('MockModuleVersion', ('id_name',
                                                     'source_version_hash',
                                                     'last_update_time'))


def call_fetch(loaded_module, params, workflow_id=1, input_dataframe=None,
               stored_dataframe=None, workflow_owner=None,
               get_input_dataframe=None, get_stored_dataframe=None,
               get_workflow_owner=None):
    """
    Call loaded_module.fetch, synchronously.

    You can pass either async getters or sync values.
    """
    def wrap(retval):
        async def inner():
            return retval
        return inner

    if get_input_dataframe is None:
        get_input_dataframe = wrap(input_dataframe)

    if get_stored_dataframe is None:
        get_stored_dataframe = wrap(stored_dataframe)

    if get_workflow_owner is None:
        get_workflow_owner = wrap(workflow_owner)

    kwargs = {
        'workflow_id': workflow_id,
        'get_input_dataframe': get_input_dataframe,
        'get_stored_dataframe': get_stored_dataframe,
        'get_workflow_owner': get_workflow_owner,
    }

    return async_to_sync(loaded_module.fetch)(params, **kwargs)


def async_mock(*, return_value):
    retval = asyncio.Future()
    retval.set_result(return_value)
    return Mock(return_value=retval)


@override_settings(IMPORTED_MODULES_ROOT=tempfile.mkdtemp())
class LoadedModuleTest(SimpleTestCase):
    def setUp(self):
        # Clear cache _before_ the test (in case other unit tests wrote to
        # the cache -- they aren't testing the cache so they may not remember
        # to wipe it) and _after_ the unit tests (so we don't leak stuff
        # that ought to be deleted).
        server.models.loaded_module.load_external_module.cache_clear()

        # tearDown() nixes our IMPORTED_MODULES_ROOT and that's good because we
        # want the directory gone when _all_ tests complete. But in _between_
        # tests, we should recreate it.
        if not os.path.isdir(settings.IMPORTED_MODULES_ROOT):
            os.mkdir(settings.IMPORTED_MODULES_ROOT)

    def tearDown(self):
        server.models.loaded_module.load_external_module.cache_clear()
        shutil.rmtree(settings.IMPORTED_MODULES_ROOT)

        super().tearDown()

    def test_load_static(self):
        # Test with a _real_ static module
        lm = LoadedModule.for_module_version_sync(
            MockModuleVersion('pastecsv', '(ignored)', 'now')
        )
        self.assertEqual(lm.name, 'pastecsv:internal')
        self.assertEqual(lm.is_external, False)
        self.assertEqual(lm.render_impl,
                         server.modules.pastecsv.PasteCSV.render)

    def test_load_dynamic(self):
        destdir = os.path.join(settings.IMPORTED_MODULES_ROOT, 'imported')
        os.makedirs(destdir)

        versiondir = os.path.join(destdir, 'abcdef')
        shutil.copytree(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'test_data',
            'imported'
        ), versiondir)

        with self.assertLogs('server.models.loaded_module'):
            lm = LoadedModule.for_module_version_sync(
                MockModuleVersion('imported', 'abcdef', 'now')
            )

        self.assertEqual(lm.name, 'imported:abcdef')
        self.assertEqual(lm.is_external, True)
        # We can't test that render_impl is exactly something, because we
        # don't have a handle on the loaded Python module outside of
        # LoadedModule. So we'll test by executing it.
        #
        # This ends up being kinda an integration test.
        with self.assertLogs('server.models.loaded_module'):
            result = lm.render(MockParams(col='A'),
                               pd.DataFrame({'A': [1, 2]}),
                               fetch_result=ProcessResult())
        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, pd.DataFrame({'A': [2, 4]}))

    def test_load_dynamic_ignore_test_py(self):
        destdir = os.path.join(settings.IMPORTED_MODULES_ROOT, 'imported')
        os.makedirs(destdir)

        versiondir = os.path.join(destdir, 'abcdef')
        shutil.copytree(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'test_data',
            'imported'
        ), versiondir)
        # write other .py files that aren't module code and should be ignored
        with open(os.path.join(versiondir, 'setup.py'), 'w'):
            pass
        with open(os.path.join(versiondir, 'test_filter.py'), 'w'):
            pass

        with self.assertLogs('server.models.loaded_module'):
            LoadedModule.for_module_version_sync(
                MockModuleVersion('imported', 'abcdef', 'now')
            )

    def test_load_dynamic_is_cached(self):
        destdir = os.path.join(settings.IMPORTED_MODULES_ROOT, 'imported')
        os.makedirs(destdir)

        versiondir = os.path.join(destdir, 'abcdef')
        shutil.copytree(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'test_data',
            'imported'
        ), versiondir)

        with self.assertLogs('server.models.loaded_module'):
            lm = LoadedModule.for_module_version_sync(
                MockModuleVersion('imported', 'abcdef', 'now')
            )

        with patch('importlib.util.module_from_spec', None):
            lm2 = LoadedModule.for_module_version_sync(
                MockModuleVersion('imported', 'abcdef', 'now')
            )

        self.assertIs(lm.render_impl, lm2.render_impl)

    def test_load_dynamic_from_none(self):
        lm = LoadedModule.for_module_version_sync(None)

        with self.assertLogs('server.models.loaded_module'):
            result = lm.render(MockParams(), pd.DataFrame({'A': [1]}),
                               fetch_result=ProcessResult())
        self.assertEqual(result, ProcessResult(
            error='Cannot render: module was deleted'
        ))

        with self.assertLogs('server.models.loaded_module'):
            result = call_fetch(lm, MockParams())
        self.assertEqual(result, ProcessResult(
            error='Cannot fetch: module was deleted'
        ))

    def test_render_static_with_fetch_result(self):
        args = None

        def render(params, table, *, fetch_result, **kwargs):
            nonlocal args
            args = (params, table, fetch_result, kwargs)
            return ProcessResult(pd.DataFrame({'A': [2]}))

        in_table = pd.DataFrame({'A': [0]})
        params = MockParams(foo='bar')
        fetch_result = ProcessResult(pd.DataFrame({'A': [1]}))
        expected = ProcessResult(pd.DataFrame({'A': [2]}))

        lm = LoadedModule('int', '1', False, render_impl=render)
        with self.assertLogs():
            result = lm.render(params, in_table, fetch_result=fetch_result)
        self.assertIs(args[0], params)
        self.assertIs(args[1], in_table)
        self.assertIs(args[2], fetch_result)
        self.assertEqual(args[3], {})
        self.assertEqual(result, expected)

    def test_render_static_with_no_kwargs(self):
        args = None

        def render(params, table):
            nonlocal args
            args = (params, table)
            return ProcessResult(pd.DataFrame({'A': [1]}))

        in_table = pd.DataFrame({'A': [0]})
        params = MockParams(foo='bar')
        expected = ProcessResult(pd.DataFrame({'A': [1]}))

        lm = LoadedModule('int', '1', False, render_impl=render)
        with self.assertLogs():
            result = lm.render(params, in_table, fetch_result=None)
        self.assertIs(args[0], params)
        self.assertIs(args[1], in_table)
        self.assertEqual(len(args), 2)
        self.assertEqual(result, expected)

    def test_render_static_exception(self):
        class Ick(Exception):
            pass

        def render(params, table, **kwargs):
            raise Ick('Oops')

        lm = LoadedModule('int', '1', False, render_impl=render)
        with self.assertLogs(level=logging.ERROR):
            result = lm.render(MockParams(), pd.DataFrame(), fetch_result=None)

        _, lineno = inspect.getsourcelines(render)

        self.assertEqual(result, ProcessResult(error=(
            f'Ick: Oops at line {lineno + 1} of test_LoadedModule.py'
        )))

    def test_render_static_default(self):
        lm = LoadedModule('int', '1', False)
        with self.assertLogs():
            result = lm.render(MockParams(), pd.DataFrame({'A': [1]}),
                               fetch_result=None)

        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1]})))

    def test_render_truncate_and_sanitize(self):
        calls = []

        retval = ProcessResult(pd.DataFrame({'A': [1]}))
        retval.truncate_in_place_if_too_big = lambda: calls.append('truncate')
        retval.sanitize_in_place = lambda: calls.append('sanitize')

        lm = LoadedModule('int', '1', False, render_impl=lambda _a, _b: retval)
        with self.assertLogs():
            lm.render(MockParams(), pd.DataFrame(), fetch_result=None)
        self.assertEqual(calls, ['truncate', 'sanitize'])

    def test_render_dynamic_with_fetch_result(self):
        args = None

        def render(table, params, *, fetch_result, **kwargs):
            nonlocal args
            args = (table, params, fetch_result, kwargs)
            return ProcessResult(pd.DataFrame({'A': [2]}))

        in_table = pd.DataFrame({'A': [0]})
        params = MockParams(foo='bar')
        fetch_result = ProcessResult(pd.DataFrame({'A': [1]}))
        expected = ProcessResult(pd.DataFrame({'A': [2]}))

        lm = LoadedModule('int', '1', True, render_impl=render)
        with self.assertLogs():
            result = lm.render(params, in_table, fetch_result=fetch_result)
        self.assertIs(args[0], in_table)
        self.assertEqual(args[1], {'foo': 'bar'})
        self.assertIs(args[2], fetch_result)
        self.assertEqual(args[3], {})
        self.assertEqual(result, expected)

    def test_render_dynamic_with_no_kwargs(self):
        args = None

        def render(table, params):
            nonlocal args
            args = (table, params)
            return ProcessResult(pd.DataFrame({'A': [1]}))

        in_table = pd.DataFrame({'A': [0]})
        params = MockParams(foo='bar')
        expected = ProcessResult(pd.DataFrame({'A': [1]}))

        lm = LoadedModule('int', '1', True, render_impl=render)
        with self.assertLogs():
            result = lm.render(params, in_table, fetch_result=None)
        self.assertIs(args[0], in_table)
        self.assertEqual(args[1], {'foo': 'bar'})
        self.assertEqual(len(args), 2)
        self.assertEqual(result, expected)

    def test_render_dynamic_exception(self):
        class Ick(Exception):
            pass

        def render(table, params, **kwargs):
            raise Ick('Oops')

        lm = LoadedModule('int', '1', True, render_impl=render)
        with self.assertLogs(level=logging.ERROR):
            result = lm.render(MockParams(), pd.DataFrame(), fetch_result=None)

        _, lineno = inspect.getsourcelines(render)
        self.assertEqual(result, ProcessResult(error=(
            f'Ick: Oops at line {lineno + 1} of test_LoadedModule.py'
        )))

    def test_render_dynamic_cannot_coerce_output(self):
        """Log and display error to user when module output is invalid."""
        def render(table, params, **kwargs):
            return {'foo': 'bar'}  # not a valid retval

        lm = LoadedModule('int', '1', True, render_impl=render)
        with self.assertLogs(level=logging.ERROR):
            result = lm.render(MockParams(), pd.DataFrame(), fetch_result=None)

        _, lineno = inspect.getsourcelines(render)
        self.assertRegex(result.error, (
            r'ValueError: ProcessResult input must only contain '
            r'\{dataframe, error, json, quick_fixes\} '
        ))

    def test_render_dynamic_default(self):
        lm = LoadedModule('int', '1', True)
        with self.assertLogs():
            result = lm.render(MockParams(), pd.DataFrame({'A': [1]}),
                               fetch_result=None)

        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1]})))

    def test_fetch_default_none(self):
        lm = LoadedModule('int', '1', True)
        with self.assertLogs():
            result = call_fetch(lm, MockParams())

        self.assertIsNone(result)

    def test_fetch_get_workflow_owner(self):
        # No need to make get_workflow_owner return a User: we're mocking
        get_workflow_owner = async_mock(return_value='Mock User')

        async def fetch(params, *, get_workflow_owner, **kwargs):
            table = pd.DataFrame({'X': [await get_workflow_owner()]})
            return ProcessResult(table)

        lm = LoadedModule('int', '1', True, fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, MockParams(),
                                get_workflow_owner=get_workflow_owner)

        self.assertEqual(result,
                         ProcessResult(pd.DataFrame({'X': ['Mock User']})))

    def test_fetch_get_input_dataframe(self):
        get_input_dataframe = async_mock(return_value=pd.DataFrame({'A': [1]}))

        async def fetch(params, *, get_input_dataframe, **kwargs):
            return ProcessResult(await get_input_dataframe())

        lm = LoadedModule('int', '1', True, fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, MockParams(),
                                get_input_dataframe=get_input_dataframe)

        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1]})))

    def test_fetch_get_stored_dataframe(self):
        get_stored_dataframe = async_mock(
            return_value=pd.DataFrame({'A': [1]})
        )

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            return ProcessResult(await get_stored_dataframe())

        lm = LoadedModule('int', '1', True, fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, MockParams(),
                                get_stored_dataframe=get_stored_dataframe)

        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1]})))

    def test_fetch_workflow_id(self):
        async def fetch(params, *, workflow_id, **kwargs):
            return ProcessResult(pd.DataFrame({'A': [workflow_id]}))

        lm = LoadedModule('int', '1', True, fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, MockParams(), workflow_id=123)

        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [123]})))

    def test_fetch_static_params(self):
        async def fetch(params, *, workflow_id, **kwargs):
            # Params are a Params object
            return ProcessResult(pd.DataFrame({
                'foo': [params.get_param_string('foo')],
                'bar': [params.get_param_string('bar')],
            }))
            return ProcessResult(params.items(), columns=['key', 'val'])

        lm = LoadedModule('int', '1', False, fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, MockParams(foo='bar', bar='baz'),
                                workflow_id=123)

        self.assertEqual(result.error, '')
        self.assertEqual(result, ProcessResult(pd.DataFrame({
            'foo': ['bar'],
            'bar': ['baz'],
        })))

    def test_fetch_sync(self):
        table = pd.DataFrame({'A': [1]})

        def fetch(params, **kwargs):
            return table

        lm = LoadedModule('int', 1, True, fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, MockParams())

        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, table)

    def test_fetch_sync_no_params(self):
        table = pd.DataFrame({'A': [1]})

        def fetch(params):
            return table

        lm = LoadedModule('int', 1, True, fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, MockParams())

        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, table)

    def test_fetch_dynamic_params(self):
        async def fetch(params, *, workflow_id, **kwargs):
            # Params are a dict
            return ProcessResult(pd.DataFrame({
                'foo': [params['foo']],
                'bar': [params['bar']],
            }))
            return ProcessResult(params.items(), columns=['key', 'val'])

        lm = LoadedModule('int', '1', True, fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, MockParams(foo='bar', bar='baz'),
                                workflow_id=123)

        self.assertEqual(result.error, '')
        self.assertEqual(result, ProcessResult(pd.DataFrame({
            'foo': ['bar'],
            'bar': ['baz'],
        })))

    def test_fetch_static_exception(self):
        class Ick(Exception):
            pass

        async def fetch(params, **kwargs):
            raise Ick('Oops')

        lm = LoadedModule('int', '1', False, fetch_impl=fetch)
        with self.assertLogs(level=logging.ERROR):
            result = call_fetch(lm, MockParams())

        _, lineno = inspect.getsourcelines(fetch)
        self.assertEqual(result, ProcessResult(error=(
            f'Ick: Oops at line {lineno + 1} of test_LoadedModule.py'
        )))

    def test_fetch_dynamic_exception(self):
        class Ick(Exception):
            pass

        async def fetch(params, **kwargs):
            raise Ick('Oops')

        lm = LoadedModule('int', '1', True, fetch_impl=fetch)
        with self.assertLogs(level=logging.ERROR):
            result = call_fetch(lm, MockParams())

        _, lineno = inspect.getsourcelines(fetch)
        self.assertEqual(result, ProcessResult(error=(
            f'Ick: Oops at line {lineno + 1} of test_LoadedModule.py'
        )))

    def test_migrate_params_default(self):
        lm = LoadedModule('x', '1', True, migrate_params_impl=None)
        result = lm.migrate_params(ParamDTypeDict({
            'missing': ParamDTypeString(default='x'),
            'wrong_type': ParamDTypeBoolean(),
            'ok': ParamDTypeInteger(),
        }), {'wrong_type': 'true', 'ok': 3})
        self.assertEqual(result, {'missing': 'x', 'wrong_type': True, 'ok': 3})

    def test_migrate_params_impl(self):
        def migrate_params(params):
            return {
                'x': params['a'],
                'y': params['b']
            }

        schema = ParamDTypeDict({
            'x': ParamDTypeInteger(),
            'y': ParamDTypeInteger(),
        })

        lm = LoadedModule('x', '1', True, migrate_params_impl=migrate_params)
        result = lm.migrate_params(schema, {'a': 1, 'b': 2})
        self.assertEqual(result, {'x': 1, 'y': 2})

    def test_migrate_params_impl_exception(self):
        def migrate_params(params):
            raise KeyError

        lm = LoadedModule('x', '1', True,
                          migrate_params_impl=migrate_params)
        with self.assertRaises(ValueError):
            lm.migrate_params([], {})

    def test_migrate_params_impl_missing_output(self):
        lm = LoadedModule('x', '1', True, migrate_params_impl=lambda x: x)
        with self.assertRaises(ValueError):
            lm.migrate_params(
                ParamDTypeDict({'x': ParamDTypeString()}),
                {}  # should have 'x' key
            )

    def test_migrate_params_impl_wrong_output_type(self):
        lm = LoadedModule('x', '1', True, migrate_params_impl=lambda x: x)
        with self.assertRaises(ValueError):
            lm.migrate_params(
                ParamDTypeDict({'x': ParamDTypeString()}),
                {'x': 2}  # should be str
            )

    def test_migrate_params_impl_extra_output(self):
        lm = LoadedModule('x', '1', True, migrate_params_impl=lambda x: x)
        with self.assertRaises(ValueError):
            lm.migrate_params(
                ParamDTypeDict({}),
                {'x': 'should not be here'}
            )
