import uuid
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from typing import List

import pyarrow as pa

from cjwkernel.types import (
    Column,
    ColumnType,
    LoadedRenderResult,
    RenderError,
    Tab,
    TabOutput,
)
from cjwkernel.util import tempdir_context
from cjwstate import s3
from cjwstate.models import Workflow, UploadedFile
from cjwstate.modules.param_dtype import ParamDType
from cjwstate.tests.utils import DbTestCase
from renderer.execute.renderprep import clean_value, RenderContext
from renderer.execute.types import (
    StepResult,
    TabCycleError,
    TabOutputUnreachableError,
    PromptingError,
)


def NUMBER(name: str, format: str = "{:,}"):
    return Column(name, ColumnType.Number(format=format))


def TEXT(name: str):
    return Column(name, ColumnType.Text())


def TIMESTAMP(name: str):
    return Column(name, ColumnType.Timestamp())


class CleanValueTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.exit_stack = ExitStack()
        self.basedir = self.exit_stack.enter_context(tempdir_context())

    def tearDown(self):
        self.exit_stack.close()
        super().tearDown()

    def _render_context(
        self,
        *,
        step_id=None,
        input_table_columns=None,
        tab_results={},
        params={},
        exit_stack=None,
    ) -> RenderContext:
        if exit_stack is None:
            exit_stack = self.exit_stack
        return RenderContext(
            step_id=step_id,
            input_table_columns=input_table_columns,
            tab_results=tab_results,
            basedir=self.basedir,
            exit_stack=exit_stack,
            params=params,
        )

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
        step = tab.steps.create(module_id_name="uploadfile", order=0, slug="step-1")
        id = str(uuid.uuid4())
        key = f"wf-${workflow.id}/wfm-${step.id}/${id}"
        s3.put_bytes(s3.UserFilesBucket, key, b"1234")
        UploadedFile.objects.create(
            step=step, name="x.csv.gz", size=4, uuid=id, key=key
        )
        with ExitStack() as inner_stack:
            context = self._render_context(step_id=step.id, exit_stack=inner_stack)
            result: Path = clean_value(ParamDType.File(), id, context)
            self.assertIsInstance(result, Path)
            self.assertEqual(result.read_bytes(), b"1234")
            self.assertEqual(result.suffixes, [".csv", ".gz"])

        # Assert that once `exit_stack` goes out of scope, file is deleted
        self.assertFalse(result.exists())

    def test_clean_file_no_uploaded_file(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(module_id_name="uploadfile", order=0, slug="step-1")
        context = self._render_context(step_id=step.id)
        result = clean_value(ParamDType.File(), str(uuid.uuid4()), context)
        self.assertIsNone(result)
        # Assert that if a temporary file was created to house the download, it
        # no longer exists.
        self.assertListEqual(list(self.basedir.iterdir()), [])

    def test_clean_file_no_s3_file(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(module_id_name="uploadfile", order=0, slug="step-1")
        step2 = tab.steps.create(module_id_name="uploadfile", order=1, slug="step-2")
        id = str(uuid.uuid4())
        key = f"wf-${workflow.id}/wfm-${step.id}/${id}"
        # Oops -- let's _not_ put the file!
        # s3.put_bytes(s3.UserFilesBucket, key, b'1234')
        UploadedFile.objects.create(
            step=step2, name="x.csv.gz", size=4, uuid=id, key=key
        )
        context = self._render_context(step_id=step.id)
        result = clean_value(ParamDType.File(), id, context)
        self.assertIsNone(result)
        # Assert that if a temporary file was created to house the download, it
        # no longer exists.
        self.assertListEqual(list(self.basedir.iterdir()), [])

    def test_clean_file_wrong_step(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(module_id_name="uploadfile", order=0, slug="step-1")
        step2 = tab.steps.create(module_id_name="uploadfile", order=1, slug="step-2")
        id = str(uuid.uuid4())
        key = f"wf-${workflow.id}/wfm-${step.id}/${id}"
        s3.put_bytes(s3.UserFilesBucket, key, b"1234")
        UploadedFile.objects.create(
            step=step2, name="x.csv.gz", size=4, uuid=id, key=key
        )
        context = self._render_context(step_id=step.id)
        result = clean_value(ParamDType.File(), id, context)
        self.assertIsNone(result)
        # Assert that if a temporary file was created to house the download, it
        # no longer exists.
        self.assertListEqual(list(self.basedir.iterdir()), [])

    def test_clean_normal_dict(self):
        context = self._render_context()
        schema = ParamDType.Dict(
            {"str": ParamDType.String(), "int": ParamDType.Integer()}
        )
        value = {"str": "foo", "int": 3}
        expected = dict(value)  # no-op
        result = clean_value(schema, value, context)
        self.assertEqual(result, expected)

    def test_clean_column_valid(self):
        context = self._render_context(input_table_columns=[TEXT("A")])
        result = clean_value(ParamDType.Column(), "A", context)
        self.assertEqual(result, "A")

    def test_clean_column_prompting_error_convert_to_text(self):
        # TODO make this _automatic_ instead of quick-fix?
        # Consider Regex. We probably want to pass the module a text Series
        # _separately_ from the input DataFrame. That way Regex can output
        # a new Text column but preserve its input column's data type.
        #
        # ... but for now: prompt for a Quick Fix.
        context = self._render_context(input_table_columns=[NUMBER("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Column(column_types=frozenset({"text"})), "A", context
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], None, frozenset({"text"}))],
        )

    def test_clean_column_prompting_error_convert_to_number(self):
        context = self._render_context(input_table_columns=[TEXT("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Column(column_types=frozenset({"number"})), "A", context
            )
        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], "text", frozenset({"number"}))],
        )

    def test_list_prompting_error_concatenate_same_type(self):
        context = self._render_context(input_table_columns=[TEXT("A"), TEXT("B")])
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
        context = self._render_context(input_table_columns=[TEXT("A"), TIMESTAMP("B")])
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
                    ["B"], "timestamp", frozenset({"number"})
                ),
            ],
        )

    def test_list_prompting_error_concatenate_different_type_to_text(self):
        context = self._render_context(
            input_table_columns=[NUMBER("A"), TIMESTAMP("B")]
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
        context = self._render_context(input_table_columns=[TEXT("A"), TEXT("B")])
        schema = ParamDType.Dict(
            {
                "col1": ParamDType.Column(column_types=frozenset({"number"})),
                "col2": ParamDType.Column(column_types=frozenset({"timestamp"})),
            }
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, {"col1": "A", "col2": "B"}, context)

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(["B"], "text", frozenset({"timestamp"})),
            ],
        )

    def test_dict_prompting_error_concatenate_same_type(self):
        context = self._render_context(input_table_columns=[TEXT("A"), TEXT("B")])
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
        context = self._render_context(input_table_columns=[TEXT("A"), TIMESTAMP("B")])
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
                    ["B"], "timestamp", frozenset({"number"})
                ),
            ],
        )

    def test_clean_column_missing_becomes_empty_string(self):
        context = self._render_context(input_table_columns=[TEXT("A")])
        result = clean_value(ParamDType.Column(), "B", context)
        self.assertEqual(result, "")

    def test_clean_multicolumn_valid(self):
        context = self._render_context(input_table_columns=[TEXT("A"), TEXT("B")])
        result = clean_value(ParamDType.Multicolumn(), ["A", "B"], context)
        self.assertEqual(result, ["A", "B"])

    def test_clean_multicolumn_sort_in_table_order(self):
        context = self._render_context(input_table_columns=[TEXT("B"), TEXT("A")])
        result = clean_value(ParamDType.Multicolumn(), ["A", "B"], context)
        self.assertEqual(result, ["B", "A"])

    def test_clean_multicolumn_prompting_error_convert_to_text(self):
        context = self._render_context(
            input_table_columns=[NUMBER("A"), TIMESTAMP("B"), TEXT("C")]
        )
        with self.assertRaises(PromptingError) as cm:
            schema = ParamDType.Multicolumn(column_types=frozenset({"text"}))
            clean_value(schema, ["A", "B"], context)

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], None, frozenset({"text"}))],
        )

    def test_clean_multicolumn_missing_is_removed(self):
        context = self._render_context(input_table_columns=[TEXT("A"), TEXT("B")])
        result = clean_value(ParamDType.Multicolumn(), ["A", "X", "B"], context)
        self.assertEqual(result, ["A", "B"])

    def test_clean_multichartseries_missing_is_removed(self):
        context = self._render_context(input_table_columns=[NUMBER("A"), NUMBER("B")])
        value = [
            {"column": "A", "color": "#aaaaaa"},
            {"column": "C", "color": "#cccccc"},
        ]
        result = clean_value(ParamDType.Multichartseries(), value, context)
        self.assertEqual(result, [{"column": "A", "color": "#aaaaaa"}])

    def test_clean_multichartseries_non_number_is_prompting_error(self):
        context = self._render_context(input_table_columns=[TEXT("A"), TIMESTAMP("B")])
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
                    ["B"], "timestamp", frozenset({"number"})
                ),
            ],
        )

    def test_clean_tab_happy_path(self):
        tab = Tab("tab-1", "Tab 1")
        context = self._render_context(
            tab_results={tab: StepResult(Path("tab-1.arrow"), [TEXT("A")])}
        )
        result = clean_value(ParamDType.Tab(), "tab-1", context)
        self.assertEqual(result, TabOutput(tab, "tab-1.arrow"))

    def test_clean_multicolumn_from_other_tab(self):
        tab2 = Tab("tab-2", "Tab 2")

        schema = ParamDType.Dict(
            {
                "tab": ParamDType.Tab(),
                "columns": ParamDType.Multicolumn(tab_parameter="tab"),
            }
        )
        params = {"tab": "tab-2", "columns": ["A-from-tab-1", "A-from-tab-2"]}
        context = self._render_context(
            input_table_columns=[NUMBER("A-from-tab-1")],
            tab_results={
                tab2: StepResult(Path("tab-2.arrow"), [NUMBER("A-from-tab-2")])
            },
            params=params,
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
        context = self._render_context(
            input_table_columns=[NUMBER("A-from-tab-1")],
            tab_results={},
            params=params,
        )
        result = clean_value(schema, params, context)
        # result['tab'] is not what we're testing here
        self.assertEqual(result["columns"], [])

    def test_clean_tab_no_tab_selected_gives_none(self):
        context = self._render_context(tab_results={})
        result = clean_value(ParamDType.Tab(), "", context)
        self.assertEqual(result, None)

    def test_clean_tab_missing_tab_selected_gives_none(self):
        # If the user has selected a nonexistent tab, pretend tab is blank.
        #
        # JS sees nonexistent tab slugs. render() doesn't.
        context = self._render_context(tab_results={})
        result = clean_value(ParamDType.Tab(), "tab-XXX", context)
        self.assertEqual(result, None)

    def test_clean_tab_cycle(self):
        tab = Tab("tab-1", "Tab 1")
        context = self._render_context(tab_results={tab: None})
        with self.assertRaises(TabCycleError):
            clean_value(ParamDType.Tab(), "tab-1", context)

    def test_clean_tab_unreachable(self):
        tab = Tab("tab-error", "Buggy Tab")
        context = self._render_context(
            tab_results={tab: StepResult(Path("tab-error.arrow"), [])}
        )
        with self.assertRaises(TabOutputUnreachableError):
            clean_value(ParamDType.Tab(), "tab-error", context)

    def test_clean_tabs_happy_path(self):
        tab2 = Tab("tab-2", "Tab 2")
        tab3 = Tab("tab-3", "Tab 3")

        context = self._render_context(
            tab_results={
                tab2: StepResult(Path("tab-2.arrow"), [NUMBER("B")]),
                tab3: StepResult(Path("tab-3.arrow"), [NUMBER("C")]),
            }
        )
        result = clean_value(ParamDType.Multitab(), ["tab-2", "tab-3"], context)
        self.assertEqual(
            result, [TabOutput(tab2, "tab-2.arrow"), TabOutput(tab3, "tab-3.arrow")]
        )

    def test_clean_tabs_preserve_ordering(self):
        tab2 = Tab("tab-2", "Tab 2")
        tab3 = Tab("tab-3", "Tab 3")

        context = self._render_context(
            # RenderContext's dict ordering determines desired tab order.
            tab_results={
                tab3: StepResult(Path("tab-3.arrow"), [NUMBER("C")]),
                tab2: StepResult(Path("tab-2.arrow"), [NUMBER("B")]),
            }
        )
        # Supply wrongly-ordered tabs; renderprep should reorder them.
        result = clean_value(ParamDType.Multitab(), ["tab-2", "tab-3"], context)
        self.assertEqual(
            result, [TabOutput(tab3, "tab-3.arrow"), TabOutput(tab2, "tab-2.arrow")]
        )

    def test_clean_tabs_nix_missing_tab(self):
        context = self._render_context(tab_results={})
        result = clean_value(ParamDType.Multitab(), ["tab-missing"], context)
        self.assertEqual(result, [])

    def test_clean_tabs_tab_cycle(self):
        tab = Tab("tab-1", "Tab 1")
        context = self._render_context(tab_results={tab: None})
        with self.assertRaises(TabCycleError):
            clean_value(ParamDType.Multitab(), ["tab-1"], context)

    def test_clean_tabs_tab_unreachable(self):
        tab = Tab("tab-1", "Tab 1")
        context = self._render_context(
            tab_results={tab: StepResult(Path("tab-1.arrow"), [])}
        )
        with self.assertRaises(TabOutputUnreachableError):
            clean_value(ParamDType.Multitab(), ["tab-1"], context)

    def test_clean_condition_empty_and_and_or_are_none(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": []}],
                },
                context,
            ),
            None,
        )

    def test_clean_condition_empty_column_is_none(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "text_is",
                    "column": "",
                    "value": "",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            ),
            None,
        )
        # And test it in the context of a broader and/or
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "and",
                    "conditions": [
                        {
                            "operation": "or",
                            "conditions": [
                                {
                                    "operation": "text_is",
                                    "column": "",
                                    "value": "",
                                    "isCaseSensitive": False,
                                    "isRegex": False,
                                }
                            ],
                        }
                    ],
                },
                context,
            ),
            None,
        )

    def test_clean_condition_and_or_simplify(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "and",
                    "conditions": [
                        {
                            "operation": "or",
                            "conditions": [
                                {
                                    "operation": "cell_is_blank",
                                    "column": "A",
                                    "value": "",
                                    "isCaseSensitive": False,
                                    "isRegex": False,
                                },
                            ],
                        },
                    ],
                },
                context,
            ),
            {
                "operation": "cell_is_blank",
                "column": "A",
            },
        )

    def test_clean_condition_and_or_multiple_conditions(self):
        context = self._render_context(input_table_columns=[TEXT("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "and",
                    "conditions": [
                        {
                            "operation": "or",
                            "conditions": [
                                {
                                    "operation": "cell_is_blank",
                                    "column": "A",
                                    "value": "",
                                    "isCaseSensitive": False,
                                    "isRegex": False,
                                },
                                {
                                    "operation": "cell_is_null",
                                    "column": "A",
                                    "value": "",
                                    "isCaseSensitive": False,
                                    "isRegex": False,
                                },
                            ],
                        },
                        {
                            "operation": "text_is",
                            "column": "A",
                            "value": "",
                            "isCaseSensitive": False,
                            "isRegex": False,
                        },
                    ],
                },
                context,
            ),
            {
                "operation": "and",
                "conditions": [
                    {
                        "operation": "or",
                        "conditions": [
                            {
                                "operation": "cell_is_blank",
                                "column": "A",
                            },
                            {
                                "operation": "cell_is_null",
                                "column": "A",
                            },
                        ],
                    },
                    {
                        "operation": "text_is",
                        "column": "A",
                        "value": "",
                        "isCaseSensitive": False,
                        "isRegex": False,
                    },
                ],
            },
        )

    def test_clean_condition_missing_column_is_none(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "text_is",
                    "column": "B",
                    "value": "",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            ),
            None,
        )

    def test_clean_condition_text_wrong_type(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "text_is",
                    "column": "A",
                    "value": "",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], None, frozenset({"text"}))],
        )

    def test_clean_condition_text_happy_path(self):
        context = self._render_context(input_table_columns=[TEXT("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "text_is",
                    "column": "A",
                    "value": "a",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            ),
            {
                "operation": "text_is",
                "column": "A",
                "value": "a",
                "isCaseSensitive": False,
                "isRegex": False,
            },
        )

    def test_clean_condition_not(self):
        context = self._render_context(input_table_columns=[TEXT("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "text_is_not",
                    "column": "A",
                    "value": "a",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            ),
            {
                "operation": "not",
                "condition": {
                    "operation": "text_is",
                    "column": "A",
                    "value": "a",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
            },
        )

    def test_clean_condition_not_with_subclause_error(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "text_is",
                    "column": "A",
                    "value": "",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], None, frozenset({"text"}))],
        )

    def test_clean_condition_number_wrong_column_type(self):
        context = self._render_context(input_table_columns=[TEXT("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "number_is",
                    "column": "A",
                    "value": "1",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], "text", frozenset({"number"}))],
        )

    def test_clean_condition_number_wrong_value(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "number_is",
                    "column": "A",
                    "value": "bad",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            )

        self.assertEqual(
            cm.exception.errors, [PromptingError.CannotCoerceValueToNumber("bad")]
        )

    def test_clean_condition_number_wrong_column_type_and_wrong_value(self):
        context = self._render_context(input_table_columns=[TEXT("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "number_is",
                    "column": "A",
                    "value": "bad",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            )

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.CannotCoerceValueToNumber("bad"),
            ],
        )

    def test_clean_condition_number_happy_path(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "number_is",
                    "column": "A",
                    "value": "1",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            ),
            {
                "operation": "number_is",
                "column": "A",
                "value": 1,
            },
        )

    def test_clean_condition_timestamp_wrong_column_type(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "timestamp_is_greater_than",
                    "column": "A",
                    "value": "2020-01-01T00:00Z",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            )

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(
                    ["A"], "number", frozenset({"timestamp"})
                ),
            ],
        )

    def test_clean_condition_timestamp_wrong_value(self):
        context = self._render_context(input_table_columns=[TIMESTAMP("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "timestamp_is_greater_than",
                    "column": "A",
                    "value": "Yesterday",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            )

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.CannotCoerceValueToTimestamp("Yesterday"),
            ],
        )

    def test_clean_condition_timestamp_wrong_column_type_and_wrong_value(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "timestamp_is_greater_than",
                    "column": "A",
                    "value": "Yesterday",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            )

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(
                    ["A"], "number", frozenset({"timestamp"})
                ),
                PromptingError.CannotCoerceValueToTimestamp("Yesterday"),
            ],
        )

    def test_clean_condition_timestamp_happy_path(self):
        context = self._render_context(input_table_columns=[TIMESTAMP("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "timestamp_is_greater_than",
                    "column": "A",
                    "value": "2020-11-01",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            ),
            {
                "operation": "timestamp_is_greater_than",
                "column": "A",
                "value": "2020-11-01",
            },
        )

    def test_clean_condition_untyped(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "cell_is_blank",
                    "column": "A",
                    "value": "2020-11-01",
                    "isCaseSensitive": True,
                    "isRegex": False,
                },
                context,
            ),
            {
                "operation": "cell_is_blank",
                "column": "A",
            },
        )

    def test_clean_condition_no_operation(self):
        context = self._render_context(input_table_columns=[NUMBER("A")])
        self.assertEqual(
            clean_value(
                ParamDType.Condition(),
                {
                    "operation": "",
                    "column": "A",
                    "value": "foo",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                context,
            ),
            None,
        )
