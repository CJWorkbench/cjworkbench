import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import Column, ColumnType, ProcessResult, TableShape, \
        StepResultShape
from server.models import Params, Workflow
from server.models.param_field import ParamDType
from server.tests.utils import DbTestCase
from worker.execute.renderprep import clean_value, RenderContext
from worker.execute.types import TabCycleError, TabOutputUnreachableError, \
        UnneededExecution


class CleanValueTests(DbTestCase):
    def test_clean_normal_dict(self):
        context = RenderContext(None, None, None, None)
        schema = ParamDType.Dict({
            'str': ParamDType.String(),
            'int': ParamDType.Integer(),
        })
        value = {'str': 'foo', 'int': 3}
        expected = dict(value)  # no-op
        result = clean_value(schema, value, context)
        self.assertEqual(result, expected)

    def test_clean_column_valid(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER),
        ]), None, None)
        schema = ParamDType.Dict({
            'column': ParamDType.Column(),
        })
        value = {'column': 'A'}
        result = clean_value(schema, value, context)
        self.assertEqual(result, {'column': 'A'})

    def test_clean_column_missing_becomes_empty_string(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER),
        ]), None, None)
        schema = ParamDType.Dict({
            'column': ParamDType.Column(),
        })
        value = {'column': 'B'}
        result = clean_value(schema, value, context)
        self.assertEqual(result, {'column': ''})

    def test_clean_multicolumn_valid(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER),
            Column('B', ColumnType.NUMBER),
        ]), None, None)
        schema = ParamDType.Dict({
            'columns': ParamDType.Multicolumn(),
        })
        value = {'columns': 'A,B'}
        result = clean_value(schema, value, context)
        self.assertEqual(result, {'columns': 'A,B'})

    def test_clean_multicolumn_missing_is_removed(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER),
            Column('B', ColumnType.NUMBER),
        ]), None, None)
        schema = ParamDType.Dict({
            'columns': ParamDType.Multicolumn(),
        })
        value = {'columns': 'A,X,B'}
        result = clean_value(schema, value, context)
        self.assertEqual(result, {'columns': 'A,B'})

    def test_clean_tab_happy_path(self):
        tab_output = ProcessResult(pd.DataFrame({'A': [1, 2]}))
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wfm = tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=workflow.last_delta_id
        )
        wfm.cache_render_result(workflow.last_delta_id, tab_output)

        context = RenderContext(workflow.id, None, {
            tab.slug: StepResultShape('ok', tab_output.table_shape),
        }, None)
        schema = ParamDType.Dict({'tab': ParamDType.Tab()})

        result = clean_value(schema, {'tab': tab.slug}, context)
        self.assertEqual(result['tab'].slug, tab.slug)
        self.assertEqual(result['tab'].name, tab.name)
        self.assertEqual(result['tab'].columns, [
            Column('A', ColumnType.NUMBER),
        ])
        assert_frame_equal(result['tab'].dataframe,
                           pd.DataFrame({'A': [1, 2]}))

    def test_clean_multicolumn_from_other_tab(self):
        tab_output = ProcessResult(pd.DataFrame({'A-from-tab-2': [1, 2]}))
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wfm = tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=workflow.last_delta_id
        )
        wfm.cache_render_result(workflow.last_delta_id, tab_output)

        schema = ParamDType.Dict({
            'tab': ParamDType.Tab(),
            'columns': ParamDType.Multicolumn(tab_parameter='tab'),
        })
        param_values = {'tab': tab.slug,
                        'columns': 'A-from-tab-1,A-from-tab-2'}
        params = Params(schema, param_values, {})
        context = RenderContext(workflow.id, TableShape(3, [
            Column('A-from-tab-1', ColumnType.NUMBER),
        ]), {
            tab.slug: StepResultShape('ok', tab_output.table_shape),
        }, params)
        result = clean_value(schema, param_values, context)
        # result['tab'] is not what we're testing here
        self.assertEqual(result['columns'], 'A-from-tab-2')

    def test_clean_tab_no_tab_selected_gives_none(self):
        context = RenderContext(None, None, {}, None)
        schema = ParamDType.Dict({'tab': ParamDType.Tab()})
        result = clean_value(schema, {'tab': ''}, context)
        self.assertEqual(result, {'tab': None})

    def test_clean_tab_missing_tab_selected_gives_none(self):
        """
        If the user has selected a nonexistent tab, pretend tab is blank.

        The JS side of things will see the nonexistent tab, but not render().
        """
        context = RenderContext(None, None, {}, None)
        schema = ParamDType.Dict({'tab': ParamDType.Tab()})
        result = clean_value(schema, {'tab': 'tab-XXX'}, context)
        self.assertEqual(result, {'tab': None})

    def test_clean_tab_no_tab_output_raises_cycle(self):
        context = RenderContext(None, None, {'tab-1': None}, None)
        schema = ParamDType.Dict({'tab': ParamDType.Tab()})
        with self.assertRaises(TabCycleError):
            clean_value(schema, {'tab': 'tab-1'}, context)

    def test_clean_tab_tab_error_raises_cycle(self):
        shape = StepResultShape('error', TableShape(0, []))
        context = RenderContext(None, None, {'tab-1': shape}, None)
        schema = ParamDType.Dict({'tab': ParamDType.Tab()})
        with self.assertRaises(TabOutputUnreachableError):
            clean_value(schema, {'tab': 'tab-1'}, context)

    def test_clean_tab_tab_delete_race_raises_unneededexecution(self):
        """
        If a user deletes the tab during render, raise UnneededExecution.

        It doesn't really matter _what_ the return value is, since the render()
        result will never be saved if this WfModule's delta has changed.
        UnneededExecution just seems like the quickest way out of this mess:
        it's an error the caller is meant to raise anyway, unlike
        `Tab.DoesNotExist`.
        """
        # tab_output is what 'render' _thinks_ the output should be
        tab_output = ProcessResult(pd.DataFrame({'A': [1, 2]}))

        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wfm = tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=workflow.last_delta_id
        )
        wfm.cache_render_result(workflow.last_delta_id, tab_output)
        tab.is_deleted = True
        tab.save(update_fields=['is_deleted'])
        # Simulate reality: wfm.last_relevant_delta_id will change
        wfm.last_relevant_delta_id += 1
        wfm.save(update_fields=['last_relevant_delta_id'])

        context = RenderContext(workflow.id, None, {
            tab.slug: StepResultShape('ok', tab_output.table_shape),
        }, None)
        schema = ParamDType.Dict({'tab': ParamDType.Tab()})

        with self.assertRaises(UnneededExecution):
            clean_value(schema, {'tab': tab.slug}, context)

    def test_clean_tab_wf_module_changed_raises_unneededexecution(self):
        """
        If a user changes tabs' output during render, raise UnneededExecution.

        It doesn't really matter _what_ the return value is, since the render()
        result will never be saved if this WfModule's delta has changed.
        UnneededExecution seems like the simplest contract to enforce.
        """
        # tab_output is what 'render' _thinks_ the output should be
        tab_output = ProcessResult(pd.DataFrame({'A': [1, 2]}))

        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wfm = tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=workflow.last_delta_id
        )
        wfm.cache_render_result(workflow.last_delta_id, tab_output)
        # Simulate reality: wfm.last_relevant_delta_id will change
        wfm.last_relevant_delta_id += 1
        wfm.save(update_fields=['last_relevant_delta_id'])

        context = RenderContext(workflow.id, None, {
            tab.slug: StepResultShape('ok', tab_output.table_shape),
        }, None)
        schema = ParamDType.Dict({'tab': ParamDType.Tab()})

        with self.assertRaises(UnneededExecution):
            clean_value(schema, {'tab': tab.slug}, context)
