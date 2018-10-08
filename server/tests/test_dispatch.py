import io
from django.test import TestCase, override_settings
import numpy as np
import pandas as pd
from server.tests.utils import mock_csv_table
from server.dispatch import module_dispatch_render
from server.modules.types import ProcessResult
from server.tests.modules.util import MockParams


P = MockParams.factory(colnames=(['M', 'F'], []))


class Module:
    def __init__(self, id_name):
        self.id_name = id_name
        self.dispatch = id_name


class ModuleVersion:
    def __init__(self, id_name, version):
        self.module = Module(id_name)
        self.source_version_hash=version


select_columns = (
    ModuleVersion('selectcolumns', '1.0'),
    MockParams(colnames=(['M', 'F'], []), drop_or_keep=1, select_range=False)
)
invalid_python_code = (
    ModuleVersion('pythoncode', '1.0'),
    MockParams(code='not valid python')
)


class DispatchTests(TestCase):
    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super().setUp()

        self.test_table = pd.DataFrame({
            'Class': ['math', 'english', 'history', 'economics'],
            'M': [10, np.nan, 11, 20],
            'F': [12, 7, 13, 20],
        })

    # basic internal render test
    def test_internal_render(self):
        result = module_dispatch_render(*select_columns, self.test_table, None)
        self.assertEqual(result, ProcessResult(pd.DataFrame({
            'M': [10, np.nan, 11, 20],
            'F': [12, 7, 13, 20],
        })))

    def test_external_render(self):
        # External modules take a different code path,
        # but this is tested in test_importfromgithub.test_load_and_dispatch
        pass

    # should return empty table if module is missing (not, for example, None)
    def test_missing_module(self):
        result = module_dispatch_render(None, MockParams(),
                                        self.test_table, None)
        self.assertEqual(result, ProcessResult(
            error='This module code has been uninstalled. Please delete it.'
        ))

    def test_error_render(self):
        # Force an error, ensure that it's returned and the output is a NOP
        result = module_dispatch_render(*invalid_python_code,
                                        self.test_table, None)
        self.assertEqual(result, ProcessResult(
            error='Line 1: invalid syntax (user input, line 1)',
            json={'output': ''}  # not part of this test
        ))

    def test_render_fetch_result(self):
        # We'll render loadurl, because its render() function just returns the
        # fetch result.
        table = pd.DataFrame({'A': [1, 2]})
        result = module_dispatch_render(ModuleVersion('loadurl', '1.0'),
                                        MockParams(url='http://example.org/foo.csv',
                                                   has_header=True),
                                        pd.DataFrame(), ProcessResult(table))
        self.assertEqual(result, ProcessResult(table))

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_render_static_truncates_table(self):
        table = pd.DataFrame({'A': [1, 2, 3]})
        result = module_dispatch_render(ModuleVersion('selectcolumns', '1.0'),
                                        MockParams(colnames=(['A'], []),
                                                   drop_or_keep=1,
                                                   select_range=False),
                                        table, None)
        self.assertEqual(result, ProcessResult(
            dataframe=pd.DataFrame({'A': [1, 2]}),
            error='Truncated output from 3 rows to 2'
        ))
