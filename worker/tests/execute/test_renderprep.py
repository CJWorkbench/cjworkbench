import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import Column, ColumnType, ProcessResult, TableShape, \
        RenderColumn, StepResultShape
from server.models import Params, Workflow
from server.models.param_spec import ParamDType
from server.tests.utils import DbTestCase
from worker.execute.renderprep import clean_value, RenderContext
from worker.execute.types import TabCycleError, TabOutputUnreachableError, \
        UnneededExecution, PromptingError


class CleanValueTests(DbTestCase):
    def test_clean_float(self):
        result = clean_value(ParamDType.Float(), 3.0, None)
        self.assertEqual(result, 3.0)
        self.assertIsInstance(result, float)

    def test_clean_float_with_int_value(self):
        # ParamDType.Float can have `int` values (because values come from
        # json.parse(), which only gives Numbers so can give "3" instead of
        # "3.0". We want to pass that as `float` in the `params` dict.
        result = clean_value(ParamDType.Float(), 3, None)
        self.assertEqual(result, 3.0)
        self.assertIsInstance(result, float)

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
            Column('A', ColumnType.NUMBER()),
        ]), None, None)
        result = clean_value(ParamDType.Column(), 'A', context)
        self.assertEqual(result, 'A')

    def test_clean_column_prompting_error_convert_to_text(self):
        # TODO make this _automatic_ instead of quick-fix?
        # Consider Regex. We probably want to pass the module a text Series
        # _separately_ from the input DataFrame. That way Regex can output
        # a new Text column but preserve its input column's data type.
        #
        # ... but for now: prompt for a Quick Fix.
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER()),
        ]), None, None)
        with self.assertRaises(PromptingError) as cm:
            clean_value(ParamDType.Column(column_types=frozenset({'text'})),
                        'A', context)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'number',
                                           frozenset({'text'})),
        ])

    def test_clean_column_prompting_error_convert_to_number(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.TEXT()),
        ]), None, None)
        with self.assertRaises(PromptingError) as cm:
            clean_value(ParamDType.Column(column_types=frozenset({'number'})),
                                          'A', context)
        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'text',
                                           frozenset({'number'})),
        ])

    def test_list_prompting_error_concatenate_same_type(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.TEXT()),
            Column('B', ColumnType.TEXT()),
        ]), None, None)
        schema = ParamDType.List(
            inner_dtype=ParamDType.Column(column_types=frozenset({'number'}))
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, ['A', 'B'], context)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A', 'B'], 'text',
                                           frozenset({'number'})),
        ])

    def test_list_prompting_error_concatenate_different_type(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.TEXT()),
            Column('B', ColumnType.DATETIME()),
        ]), None, None)
        schema = ParamDType.List(
            inner_dtype=ParamDType.Column(column_types=frozenset({'number'}))
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, ['A', 'B'], context)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'text',
                                           frozenset({'number'})),
            PromptingError.WrongColumnType(['B'], 'datetime',
                                           frozenset({'number'})),
        ])

    def test_dict_prompting_error(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.TEXT()),
            Column('B', ColumnType.TEXT()),
        ]), None, None)
        schema = ParamDType.Dict({
            'col1': ParamDType.Column(column_types=frozenset({'number'})),
            'col2': ParamDType.Column(column_types=frozenset({'datetime'})),
        })
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, {'col1': 'A', 'col2': 'B'}, context)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'text',
                                           frozenset({'number'})),
            PromptingError.WrongColumnType(['B'], 'text',
                                           frozenset({'datetime'})),
        ])

    def test_dict_prompting_error_concatenate_same_type(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.TEXT()),
            Column('B', ColumnType.TEXT()),
        ]), None, None)
        schema = ParamDType.Dict({
            'x': ParamDType.Column(column_types=frozenset({'number'})),
            'y': ParamDType.Column(column_types=frozenset({'number'})),
        })
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, {'x': 'A', 'y': 'B'}, context)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A', 'B'], 'text',
                                           frozenset({'number'})),
        ])

    def test_dict_prompting_error_concatenate_different_types(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.TEXT()),
            Column('B', ColumnType.DATETIME()),
        ]), None, None)
        schema = ParamDType.Dict({
            'x': ParamDType.Column(column_types=frozenset({'number'})),
            'y': ParamDType.Column(column_types=frozenset({'number'})),
        })
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, {'x': 'A', 'y': 'B'}, context)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'text',
                                           frozenset({'number'})),
            PromptingError.WrongColumnType(['B'], 'datetime',
                                           frozenset({'number'})),
        ])

    def test_clean_column_missing_becomes_empty_string(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER()),
        ]), None, None)
        result = clean_value(ParamDType.Column(), 'B', context)
        self.assertEqual(result, '')

    def test_clean_multicolumn_valid(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.NUMBER()),
        ]), None, None)
        result = clean_value(
            ParamDType.Multicolumn(),
            ['A', 'B'],
            context
        )
        self.assertEqual(result, ['A', 'B'])

    def test_clean_multicolumn_sort_in_table_order(self):
        context = RenderContext(None, TableShape(3, [
            Column('B', ColumnType.NUMBER()),
            Column('A', ColumnType.NUMBER()),
        ]), None, None)
        result = clean_value(
            ParamDType.Multicolumn(),
            ['A', 'B'],
            context
        )
        self.assertEqual(result, ['B', 'A'])

    def test_clean_column_prompting_error_convert_to_text(self):
        # TODO make this _automatic_ instead of quick-fix?
        # ... but for now: prompt for a Quick Fix.
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.DATETIME()),
            Column('C', ColumnType.TEXT()),
        ]), None, None)
        with self.assertRaises(PromptingError) as cm:
            schema = ParamDType.Multicolumn(column_types=frozenset({'text'}))
            clean_value(schema, 'A,B', context)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'number',
                                           frozenset({'text'})),
            PromptingError.WrongColumnType(['B'], 'datetime',
                                           frozenset({'text'})),
        ])

    def test_clean_multicolumn_missing_is_removed(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.NUMBER()),
        ]), None, None)
        result = clean_value(
            ParamDType.Multicolumn(),
            ['A', 'X', 'B'],
            context
        )
        self.assertEqual(result, ['A', 'B'])

    def test_clean_multichartseries_missing_is_removed(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.NUMBER()),
        ]), None, None)
        value = [
            {'column': 'A', 'color': '#aaaaaa'},
            {'column': 'C', 'color': '#cccccc'},
        ]
        result = clean_value(ParamDType.Multichartseries(), value, context)
        self.assertEqual(result, [{'column': 'A', 'color': '#aaaaaa'}])

    def test_clean_multichartseries_non_number_is_prompting_error(self):
        context = RenderContext(None, TableShape(3, [
            Column('A', ColumnType.TEXT()),
            Column('B', ColumnType.DATETIME()),
        ]), None, None)
        value = [
            {'column': 'A', 'color': '#aaaaaa'},
            {'column': 'B', 'color': '#cccccc'},
        ]
        with self.assertRaises(PromptingError) as cm:
            clean_value(ParamDType.Multichartseries(), value, context)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'text',
                                           frozenset({'number'})),
            PromptingError.WrongColumnType(['B'], 'datetime',
                                           frozenset({'number'})),
        ])

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
        result = clean_value(ParamDType.Tab(), tab.slug, context)
        self.assertEqual(result.slug, tab.slug)
        self.assertEqual(result.name, tab.name)
        self.assertEqual(result.columns, {
            'A': RenderColumn('A', 'number', '{:,}'),
        })
        assert_frame_equal(result.dataframe, pd.DataFrame({'A': [1, 2]}))

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
                        'columns': ['A-from-tab-1', 'A-from-tab-2']}
        params = Params(schema, param_values, {})
        context = RenderContext(workflow.id, TableShape(3, [
            Column('A-from-tab-1', ColumnType.NUMBER()),
        ]), {
            tab.slug: StepResultShape('ok', tab_output.table_shape),
        }, params)
        result = clean_value(schema, param_values, context)
        # result['tab'] is not what we're testing here
        self.assertEqual(result['columns'], ['A-from-tab-2'])

    def test_clean_multicolumn_from_other_tab_that_does_not_exist(self):
        # The other tab would not exist if the user selected and then deleted
        # it.
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()

        schema = ParamDType.Dict({
            'tab': ParamDType.Tab(),
            'columns': ParamDType.Multicolumn(tab_parameter='tab'),
        })
        param_values = {'tab': 'tab-missing', 'columns': ['A-from-tab']}
        params = Params(schema, param_values, {})
        context = RenderContext(workflow.id, TableShape(3, [
            Column('A-from-tab-1', ColumnType.NUMBER()),
        ]), {}, params)
        result = clean_value(schema, param_values, context)
        # result['tab'] is not what we're testing here
        self.assertEqual(result['columns'], [])

    def test_clean_tab_no_tab_selected_gives_none(self):
        context = RenderContext(None, None, {}, None)
        result = clean_value(ParamDType.Tab(), '', context)
        self.assertEqual(result, None)

    def test_clean_tab_missing_tab_selected_gives_none(self):
        """
        If the user has selected a nonexistent tab, pretend tab is blank.

        The JS side of things will see the nonexistent tab, but not render().
        """
        context = RenderContext(None, None, {}, None)
        result = clean_value(ParamDType.Tab(), 'tab-XXX', context)
        self.assertEqual(result, None)

    def test_clean_tab_no_tab_output_raises_cycle(self):
        context = RenderContext(None, None, {'tab-1': None}, None)
        with self.assertRaises(TabCycleError):
            clean_value(ParamDType.Tab(), 'tab-1', context)

    def test_clean_tab_tab_error_raises_cycle(self):
        shape = StepResultShape('error', TableShape(0, []))
        context = RenderContext(None, None, {'tab-1': shape}, None)
        with self.assertRaises(TabOutputUnreachableError):
            clean_value(ParamDType.Tab(), 'tab-1', context)

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
        with self.assertRaises(UnneededExecution):
            clean_value(ParamDType.Tab(), tab.slug, context)

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
        with self.assertRaises(UnneededExecution):
            clean_value(ParamDType.Tab(), tab.slug, context)

    def test_clean_tabs_happy_path(self):
        tab1_output = ProcessResult(pd.DataFrame({'A': [1, 2]}))
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        wfm = tab1.wf_modules.create(
            order=0,
            last_relevant_delta_id=workflow.last_delta_id
        )
        wfm.cache_render_result(workflow.last_delta_id, tab1_output)

        context = RenderContext(workflow.id, None, {
            tab1.slug: StepResultShape('ok', tab1_output.table_shape),
        }, None)
        result = clean_value(ParamDType.Multitab(), [tab1.slug], context)
        self.assertEqual(result[0].slug, tab1.slug)
        self.assertEqual(result[0].name, tab1.name)
        self.assertEqual(result[0].columns, {
            'A': RenderColumn('A', 'number', '{:,}'),
        })
        assert_frame_equal(result[0].dataframe, pd.DataFrame({'A': [1, 2]}))

    def test_clean_tabs_preserve_ordering(self):
        tab2_output = ProcessResult(pd.DataFrame({'A': [1, 2]}))
        tab3_output = ProcessResult(pd.DataFrame({'B': [2, 3]}))
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1, slug='tab-2', name='Tab 2')
        tab3 = workflow.tabs.create(position=1, slug='tab-3', name='Tab 3')
        wfm2 = tab2.wf_modules.create(
            order=0,
            last_relevant_delta_id=workflow.last_delta_id
        )
        wfm2.cache_render_result(workflow.last_delta_id, tab2_output)
        wfm3 = tab3.wf_modules.create(
            order=0,
            last_relevant_delta_id=workflow.last_delta_id
        )
        wfm3.cache_render_result(workflow.last_delta_id, tab3_output)

        # RenderContext's dict ordering determines desired tab order. (Python
        # 3.7 spec: dict is ordered in insertion order. CPython 3.6 and PyPy 7
        # do this, too.)
        context = RenderContext(workflow.id, None, {
            tab1.slug: None,
            tab2.slug: StepResultShape('ok', tab2_output.table_shape),
            tab3.slug: StepResultShape('ok', tab3_output.table_shape),
        }, None)
        # Supply wrongly-ordered tabs. Cleaned, they should be in order.
        result = clean_value(ParamDType.Multitab(),
                             [tab3.slug, tab2.slug], context)
        self.assertEqual(result[0].slug, tab2.slug)
        self.assertEqual(result[0].name, tab2.name)
        self.assertEqual(result[0].columns, {
            'A': RenderColumn('A', 'number', '{:,}'),
        })
        assert_frame_equal(result[0].dataframe, pd.DataFrame({'A': [1, 2]}))
        self.assertEqual(result[1].slug, tab3.slug)
        self.assertEqual(result[1].name, tab3.name)
        self.assertEqual(result[1].columns, {
            'B': RenderColumn('B', 'number', '{:,}'),
        })
        assert_frame_equal(result[1].dataframe, pd.DataFrame({'B': [2, 3]}))

    def test_clean_tabs_nix_missing_tab(self):
        context = RenderContext(None, None, {}, None)
        result = clean_value(ParamDType.Multitab(), ['tab-missing'], context)
        self.assertEqual(result, [])

    def test_clean_tabs_tab_error_raises_cycle(self):
        context = RenderContext(None, None, {'tab-1': None}, None)
        with self.assertRaises(TabCycleError):
            clean_value(ParamDType.Multitab(), ['tab-1'], context)
