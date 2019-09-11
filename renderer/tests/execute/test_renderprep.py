from datetime import datetime
import os
import pathlib
import uuid
import pandas as pd
from pandas.testing import assert_frame_equal
from cjwkernel.types import I18nMessage, RenderError, RenderResult, Tab, TabOutput
from cjwkernel.tests.util import arrow_table
from cjwstate import minio
from cjwstate.rendercache import cache_render_result
from cjwstate.models import Workflow, UploadedFile
from cjwstate.models.param_spec import ParamDType
from cjwstate.tests.utils import DbTestCase
from renderer.execute.renderprep import clean_value, RenderContext
from renderer.execute.types import (
    TabCycleError,
    TabOutputUnreachableError,
    PromptingError,
)


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

    def test_clean_file_none(self):
        result = clean_value(ParamDType.File(), None, None)
        self.assertEqual(result, None)

    def test_clean_file_happy_path(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wfm = tab.wf_modules.create(module_id_name="uploadfile", order=0, slug="step-1")
        id = str(uuid.uuid4())
        key = f"wf-${workflow.id}/wfm-${wfm.id}/${id}"
        minio.put_bytes(minio.UserFilesBucket, key, b"1234")
        UploadedFile.objects.create(
            wf_module=wfm,
            name="x.csv.gz",
            size=4,
            uuid=id,
            bucket=minio.UserFilesBucket,
            key=key,
        )
        context = RenderContext(wfm.id, None, {}, None)
        result = clean_value(ParamDType.File(), id, context)
        self.assertIsInstance(result, pathlib.Path)
        self.assertEqual(result.read_bytes(), b"1234")
        self.assertEqual(result.suffixes, [".csv", ".gz"])

        # Assert that once `path` goes out of scope, it's deleted
        str_path = str(result)  # get the filesystem path
        del result  # should finalize, deleting the file on the filesystem
        with self.assertRaises(FileNotFoundError):
            os.open(str_path, 0)

    def test_clean_file_no_uploaded_file(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wfm = tab.wf_modules.create(module_id_name="uploadfile", order=0, slug="step-1")
        context = RenderContext(wfm.id, None, {}, None)
        result = clean_value(ParamDType.File(), str(uuid.uuid4()), context)
        self.assertIsNone(result)

    def test_clean_file_no_minio_file(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wfm = tab.wf_modules.create(module_id_name="uploadfile", order=0, slug="step-1")
        wfm2 = tab.wf_modules.create(
            module_id_name="uploadfile", order=1, slug="step-2"
        )
        id = str(uuid.uuid4())
        key = f"wf-${workflow.id}/wfm-${wfm.id}/${id}"
        # Oops -- let's _not_ put the file!
        # minio.put_bytes(minio.UserFilesBucket, key, b'1234')
        UploadedFile.objects.create(
            wf_module=wfm2,
            name="x.csv.gz",
            size=4,
            uuid=id,
            bucket=minio.UserFilesBucket,
            key=key,
        )
        context = RenderContext(wfm.id, None, {}, None)
        result = clean_value(ParamDType.File(), id, context)
        self.assertIsNone(result)

    def test_clean_file_wrong_wf_module(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wfm = tab.wf_modules.create(module_id_name="uploadfile", order=0, slug="step-1")
        wfm2 = tab.wf_modules.create(
            module_id_name="uploadfile", order=1, slug="step-2"
        )
        id = str(uuid.uuid4())
        key = f"wf-${workflow.id}/wfm-${wfm.id}/${id}"
        minio.put_bytes(minio.UserFilesBucket, key, b"1234")
        UploadedFile.objects.create(
            wf_module=wfm2,
            name="x.csv.gz",
            size=4,
            uuid=id,
            bucket=minio.UserFilesBucket,
            key=key,
        )
        context = RenderContext(wfm.id, None, {}, None)
        result = clean_value(ParamDType.File(), id, context)
        self.assertIsNone(result)

    def test_clean_normal_dict(self):
        context = RenderContext(None, None, {}, None)
        schema = ParamDType.Dict(
            {"str": ParamDType.String(), "int": ParamDType.Integer()}
        )
        value = {"str": "foo", "int": 3}
        expected = dict(value)  # no-op
        result = clean_value(schema, value, context)
        self.assertEqual(result, expected)

    def test_clean_column_valid(self):
        context = RenderContext(None, arrow_table({"A": [1]}), {}, None)
        result = clean_value(ParamDType.Column(), "A", context)
        self.assertEqual(result, "A")

    def test_clean_column_prompting_error_convert_to_text(self):
        # TODO make this _automatic_ instead of quick-fix?
        # Consider Regex. We probably want to pass the module a text Series
        # _separately_ from the input DataFrame. That way Regex can output
        # a new Text column but preserve its input column's data type.
        #
        # ... but for now: prompt for a Quick Fix.
        context = RenderContext(None, arrow_table({"A": [1]}), {}, None)
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Column(column_types=frozenset({"text"})), "A", context
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], None, frozenset({"text"}))],
        )

    def test_clean_column_prompting_error_convert_to_number(self):
        context = RenderContext(None, arrow_table({"A": ["1"]}), {}, None)
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Column(column_types=frozenset({"number"})), "A", context
            )
        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], "text", frozenset({"number"}))],
        )

    def test_list_prompting_error_concatenate_same_type(self):
        context = RenderContext(None, arrow_table({"A": ["1"], "B": ["2"]}), {}, None)
        schema = ParamDType.List(
            inner_dtype=ParamDType.Column(column_types=frozenset({"number"}))
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, ["A", "B"], context)

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], "text", frozenset({"number"}))],
        )

    def test_list_prompting_error_concatenate_different_type(self):
        context = RenderContext(
            None, arrow_table({"A": ["1"], "B": [datetime.now()]}), {}, None
        )
        schema = ParamDType.List(
            inner_dtype=ParamDType.Column(column_types=frozenset({"number"}))
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, ["A", "B"], context)

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(
                    ["B"], "datetime", frozenset({"number"})
                ),
            ],
        )

    def test_list_prompting_error_concatenate_different_type_to_text(self):
        context = RenderContext(
            None, arrow_table({"A": [1], "B": [datetime.now()]}), {}, None
        )
        schema = ParamDType.List(
            inner_dtype=ParamDType.Column(column_types=frozenset({"text"}))
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, ["A", "B"], context)

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], None, frozenset({"text"}))],
        )

    def test_dict_prompting_error(self):
        context = RenderContext(None, arrow_table({"A": ["a"], "B": ["b"]}), {}, None)
        schema = ParamDType.Dict(
            {
                "col1": ParamDType.Column(column_types=frozenset({"number"})),
                "col2": ParamDType.Column(column_types=frozenset({"datetime"})),
            }
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, {"col1": "A", "col2": "B"}, context)

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(["B"], "text", frozenset({"datetime"})),
            ],
        )

    def test_dict_prompting_error_concatenate_same_type(self):
        context = RenderContext(None, arrow_table({"A": ["1"], "B": ["2"]}), {}, None)
        schema = ParamDType.Dict(
            {
                "x": ParamDType.Column(column_types=frozenset({"number"})),
                "y": ParamDType.Column(column_types=frozenset({"number"})),
            }
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, {"x": "A", "y": "B"}, context)

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], "text", frozenset({"number"}))],
        )

    def test_dict_prompting_error_concatenate_different_types(self):
        context = RenderContext(
            None, arrow_table({"A": ["1"], "B": [datetime.now()]}), {}, None
        )
        schema = ParamDType.Dict(
            {
                "x": ParamDType.Column(column_types=frozenset({"number"})),
                "y": ParamDType.Column(column_types=frozenset({"number"})),
            }
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, {"x": "A", "y": "B"}, context)

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(
                    ["B"], "datetime", frozenset({"number"})
                ),
            ],
        )

    def test_clean_column_missing_becomes_empty_string(self):
        context = RenderContext(None, arrow_table({"A": [1]}), {}, None)
        result = clean_value(ParamDType.Column(), "B", context)
        self.assertEqual(result, "")

    def test_clean_multicolumn_valid(self):
        context = RenderContext(None, arrow_table({"A": [1], "B": [2]}), {}, None)
        result = clean_value(ParamDType.Multicolumn(), ["A", "B"], context)
        self.assertEqual(result, ["A", "B"])

    def test_clean_multicolumn_sort_in_table_order(self):
        context = RenderContext(None, arrow_table({"B": [1], "A": [2]}), {}, None)
        result = clean_value(ParamDType.Multicolumn(), ["A", "B"], context)
        self.assertEqual(result, ["B", "A"])

    def test_clean_multicolumn_prompting_error_convert_to_text(self):
        # TODO make this _automatic_ instead of quick-fix?
        # ... but for now: prompt for a Quick Fix.
        context = RenderContext(
            None, arrow_table({"A": [1], "B": [datetime.now()], "C": ["x"]}), {}, None
        )
        with self.assertRaises(PromptingError) as cm:
            schema = ParamDType.Multicolumn(column_types=frozenset({"text"}))
            clean_value(schema, ["A", "B"], context)

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], None, frozenset({"text"}))],
        )

    def test_clean_multicolumn_missing_is_removed(self):
        context = RenderContext(None, arrow_table({"A": [1], "B": [1]}), {}, None)
        result = clean_value(ParamDType.Multicolumn(), ["A", "X", "B"], context)
        self.assertEqual(result, ["A", "B"])

    def test_clean_multichartseries_missing_is_removed(self):
        context = RenderContext(None, arrow_table({"A": [1], "B": [1]}), {}, None)
        value = [
            {"column": "A", "color": "#aaaaaa"},
            {"column": "C", "color": "#cccccc"},
        ]
        result = clean_value(ParamDType.Multichartseries(), value, context)
        self.assertEqual(result, [{"column": "A", "color": "#aaaaaa"}])

    def test_clean_multichartseries_non_number_is_prompting_error(self):
        context = RenderContext(
            None, arrow_table({"A": ["a"], "B": [datetime.now()]}), {}, None
        )
        value = [
            {"column": "A", "color": "#aaaaaa"},
            {"column": "B", "color": "#cccccc"},
        ]
        with self.assertRaises(PromptingError) as cm:
            clean_value(ParamDType.Multichartseries(), value, context)

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(
                    ["B"], "datetime", frozenset({"number"})
                ),
            ],
        )

    def test_clean_tab_happy_path(self):
        tab = Tab("tab-1", "Tab 1")
        table = arrow_table({"A": [1, 2]})
        context = RenderContext(None, None, {tab: RenderResult(table)}, None)
        result = clean_value(ParamDType.Tab(), "tab-1", context)
        self.assertEqual(result, TabOutput(tab, table))

    def test_clean_multicolumn_from_other_tab(self):
        tab2 = Tab("tab-2", "Tab 2")
        tab2_output_table = arrow_table({"A-from-tab-2": [1, 2]})

        schema = ParamDType.Dict(
            {
                "tab": ParamDType.Tab(),
                "columns": ParamDType.Multicolumn(tab_parameter="tab"),
            }
        )
        params = {"tab": "tab-2", "columns": ["A-from-tab-1", "A-from-tab-2"]}
        context = RenderContext(
            None,
            arrow_table({"A-from-tab-1": [1]}),
            {tab2: RenderResult(tab2_output_table)},
            params,
        )
        result = clean_value(schema, params, context)
        # result['tab'] is not what we're testing here
        self.assertEqual(result["columns"], ["A-from-tab-2"])

    def test_clean_multicolumn_from_other_tab_that_does_not_exist(self):
        # The other tab would not exist if the user selected and then deleted
        # it.
        schema = ParamDType.Dict(
            {
                "tab": ParamDType.Tab(),
                "columns": ParamDType.Multicolumn(tab_parameter="tab"),
            }
        )
        params = {"tab": "tab-missing", "columns": ["A-from-tab-1"]}
        context = RenderContext(None, arrow_table({"A-from-tab-1": [1]}), {}, params)
        result = clean_value(schema, params, context)
        # result['tab'] is not what we're testing here
        self.assertEqual(result["columns"], [])

    def test_clean_tab_no_tab_selected_gives_none(self):
        context = RenderContext(None, None, {}, None)
        result = clean_value(ParamDType.Tab(), "", context)
        self.assertEqual(result, None)

    def test_clean_tab_missing_tab_selected_gives_none(self):
        """
        If the user has selected a nonexistent tab, pretend tab is blank.

        JS sees nonexistent tab slugs. render() doesn't.
        """
        context = RenderContext(None, None, {}, None)
        result = clean_value(ParamDType.Tab(), "tab-XXX", context)
        self.assertEqual(result, None)

    def test_clean_tab_cycle(self):
        tab = Tab("tab-1", "Tab 1")
        context = RenderContext(None, None, {tab: None}, None)
        with self.assertRaises(TabCycleError):
            clean_value(ParamDType.Tab(), "tab-1", context)

    def test_clean_tab_unreachable(self):
        tab = Tab("tab-error", "Buggy Tab")
        context = RenderContext(None, None, {tab: RenderResult()}, None)
        with self.assertRaises(TabOutputUnreachableError):
            clean_value(ParamDType.Tab(), "tab-error", context)

    def test_clean_tabs_happy_path(self):
        tab2 = Tab("tab-2", "Tab 2")
        tab2_output = arrow_table({"B": [1]})
        tab3 = Tab("tab-3", "Tab 3")
        tab3_output = arrow_table({"C": [1]})

        context = RenderContext(
            None,
            None,
            {tab2: RenderResult(tab2_output), tab3: RenderResult(tab3_output)},
            None,
        )
        result = clean_value(ParamDType.Multitab(), ["tab-2", "tab-3"], context)
        self.assertEqual(
            result, [TabOutput(tab2, tab2_output), TabOutput(tab3, tab3_output)]
        )

    def test_clean_tabs_preserve_ordering(self):
        tab2 = Tab("tab-2", "Tab 2")
        tab2_output = arrow_table({"B": [1]})
        tab3 = Tab("tab-3", "Tab 3")
        tab3_output = arrow_table({"C": [1]})

        context = RenderContext(
            None,
            None,
            # RenderContext's dict ordering determines desired tab order.
            # (Python 3.7 spec: dict is ordered in insertion order. CPython 3.6
            # and PyPy 7 do this, too.)
            {tab3: RenderResult(tab3_output), tab2: RenderResult(tab2_output)},
            None,
        )
        # Supply wrongly-ordered tabs; renderprep should reorder them.
        result = clean_value(ParamDType.Multitab(), ["tab-2", "tab-3"], context)
        self.assertEqual([t.tab.slug for t in result], ["tab-3", "tab-2"])

    def test_clean_tabs_nix_missing_tab(self):
        context = RenderContext(None, None, {}, None)
        result = clean_value(ParamDType.Multitab(), ["tab-missing"], context)
        self.assertEqual(result, [])

    def test_clean_tabs_tab_cycle(self):
        tab = Tab("tab-1", "Tab 1")
        context = RenderContext(None, None, {tab: None}, None)
        with self.assertRaises(TabCycleError):
            clean_value(ParamDType.Multitab(), ["tab-1"], context)

    def test_clean_tabs_tab_unreachable(self):
        tab = Tab("tab-1", "Tab 1")
        context = RenderContext(None, None, {tab: RenderResult()}, None)
        with self.assertRaises(TabOutputUnreachableError):
            clean_value(ParamDType.Multitab(), ["tab-1"], context)
