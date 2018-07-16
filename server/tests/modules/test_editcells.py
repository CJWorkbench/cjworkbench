import json
from server.tests.utils import DbTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
import pandas as pd
import numpy as np
from server.models import WfModule
from server.modules.editcells import EditCells
import logging

class EditCellsTests(DbTestCase):

    def setUp(self):
        super().setUp()

        workflow = create_testdata_workflow()
        self.wf_module = load_and_add_module('editcells', workflow=workflow)
        self.pval = get_param_by_id_name('celledits')

        self.table = pd.DataFrame([
            [1,     5,      9,      10.1,   20.5,          'cake',     13,],
            [2,     6,      10,     10.2,   float('nan'),  'or',       14],
            [3,     7,      11,     10.3,   20.7,          'death',    15],
            [4,     8,      12,     10.4,   20.8,          'please',   16]],
            columns=['int1', 'int2', 'int3', 'float1', 'float2', 'string', 'unchanged'])

        self.table = self.table.astype({
            'int1': 'int64',
            'int2': 'int64',
            'int3': 'int64',
            'float1': 'float64',
            'float2': 'float64',
            'string': 'str',
            'unchanged': 'int64'
        })

    def test_edit_cells(self):
        # edit cells on a test df with cols and vals of different types.
        # - int with int val, int with float val, int with string val
        # - float with int,float,string
        # - string with int, float, string
        # - assigning multiple types to a column
        # - 0, 1, 2 values changed per column
        # - unchanged row and column
        # - NaNs in float column (should end up as empty strings if we assign a string)


        # all edit cell values are strings, because that's how they come from the client
        patch = [
            {'row': 0, 'col': 'int1', 'value':'55'},        # assign int to int
            {'row': 1, 'col': 'int1', 'value':'99'},        # two values edited in this col, both int

            {'row': 1, 'col': 'int2', 'value':'3.14'},      # assign float to int

            {'row': 1, 'col': 'int3', 'value':'bar'},       # assign string to int
            {'row': 3, 'col': 'int3', 'value':'66'},        # also assign float to the same column

            {'row': 0, 'col': 'float1', 'value': '100'},    # assign int to float
            {'row': 3, 'col': 'float2', 'value': 'baz'},    # assign string to float col with NaN's

            {'row': 3, 'col': 'string', 'value': '77'}    # assign int to string
        ]

        patched_table = pd.DataFrame([
            [55,    5,      '9',    100,    '20.5',     'cake',     13],
            [99,    3.14,   'bar',  10.2,   '',         'or',       14],
            [3,     7,      '11',   10.3,   '20.7',     'death',    15],
            [4,     8,      '66',   10.4,   'baz',      '77',       16]],
            columns=['int1', 'int2', 'int3', 'float1', 'float2', 'string', 'unchanged'])

        patched_table = patched_table.astype({
            'int1': 'int64',
            'int2': 'float64',
            'int3': 'str',
            'float1': 'float64',
            'float2': 'str',
            'string': 'str',
            'unchanged': 'int64'
        })

        self.pval.set_value(json.dumps(patch))
        self.pval.save()
        out = EditCells.render(self.wf_module, self.table)
        self.assertTrue(out.equals(patched_table))

        # check that all columns have the simplest type that will hold values (int -> float -> string)
        self.assertEqual(out['int1'].dtype, np.int64)
        self.assertEqual(out['int2'].dtype, np.float64)
        self.assertEqual(out['int3'].dtype, np.object)
        self.assertEqual(out['float1'].dtype, np.float64)
        self.assertEqual(out['float2'].dtype, np.object)
        self.assertEqual(out['string'].dtype, np.object)
        self.assertEqual(out['unchanged'].dtype, np.int64)


    def test_empty_patch(self):
        self.pval.set_value('')
        self.pval.save()
        out = EditCells.render(self.wf_module, self.table)
        self.assertTrue(out.equals(self.table))             # should NOP


    def test_empty_table(self):
        patch = [
            {'row': 0, 'col': 'int1', 'value': '55'},
            {'row': 1, 'col': 'int1', 'value': '99'}
        ]

        self.pval.set_value(json.dumps(patch))
        self.pval.save()
        out = EditCells.render(self.wf_module, pd.DataFrame())
        self.assertEqual(len(out), 0)


    def test_bad_json(self):
        # this test is supposed to log an exception, but don't print that every test
        logging.disable(logging.CRITICAL)

        self.pval.set_value('No way this is json')
        self.pval.save()
        out = EditCells.render(self.wf_module, self.table)
        self.assertEqual(self.wf_module.status, WfModule.ERROR)
        self.assertEqual(self.wf_module.error_msg, 'Internal error')
        self.assertTrue(out.equals(self.table))

        logging.disable(logging.NOTSET)

    def test_missing_cols(self):
        patch = [
            {'row': 0, 'col': 'hello', 'value': '55'},
            {'row': 1, 'col': 'kitty', 'value': '99'}
        ]
        self.pval.set_value(json.dumps(patch))
        self.pval.save()
        out = EditCells.render(self.wf_module, self.table)
        self.assertTrue(out.equals(self.table))                # should NOP
