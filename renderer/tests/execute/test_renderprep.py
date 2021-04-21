import uuid
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Dict

from cjwmodule.spec.paramschema import ParamSchema

from cjwkernel.types import Column, ColumnType, TabOutput, UploadedFile
from cjwkernel.util import tempdir_context
from cjwstate import s3
from cjwstate.models.workflow import Workflow
from cjwstate.models.uploaded_file import UploadedFile as UploadedFileModel
from cjwstate.tests.utils import DbTestCase
from renderer.execute.renderprep import PrepParamsResult, prep_params
from renderer.execute.types import (
    StepResult,
    Tab,
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

    def _call_prep_params(
        self,
        schema: ParamSchema.Dict,
        params: Dict[str, Any],
        *,
        step_id=None,
        input_table_columns=None,
        tab_results={},
        exit_stack=None,
    ) -> PrepParamsResult:
        if exit_stack is None:
            exit_stack = self.exit_stack

        return prep_params(
            step_id=step_id,
            input_table_columns=input_table_columns,
            tab_results=tab_results,
            basedir=self.basedir,
            exit_stack=exit_stack,
            schema=schema,
            params=params,
        )

    def _call_clean_value(self, schema: ParamSchema, value: Any, **kwargs) -> Any:
        result = self._call_prep_params(
            ParamSchema.Dict({"value": schema}), {"value": value}, **kwargs
        )
        return result.params["value"]

    def test_clean_float(self):
        result = self._call_clean_value(ParamSchema.Float(), 3.0)
        self.assertEqual(result, 3.0)
        self.assertIsInstance(result, float)

    def test_clean_float_with_int_value(self):
        # ParamSchema.Float can have `int` values (because values come from
        # json.parse(), which only gives Numbers so can give "3" instead of
        # "3.0". We want to pass that as `float` in the `params` dict.
        result = self._call_clean_value(ParamSchema.Float(), 3)
        self.assertEqual(result, 3.0)
        self.assertIsInstance(result, float)

    def test_clean_file_none(self):
        self.assertIsNone(self._call_clean_value(ParamSchema.File(), None))

    def test_clean_file_happy_path(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(module_id_name="uploadfile", order=0, slug="step-1")
        key = f"wf-${workflow.id}/wfm-${step.id}/6e00511a-8ac4-4b72-9acc-9d069992b5cf"
        s3.put_bytes(s3.UserFilesBucket, key, b"1234")
        model = UploadedFileModel.objects.create(
            step=step,
            name="x.csv.gz",
            size=4,
            uuid="6e00511a-8ac4-4b72-9acc-9d069992b5cf",
            key=key,
        )
        with ExitStack() as inner_stack:
            result = self._call_prep_params(
                ParamSchema.Dict({"file": ParamSchema.File()}),
                {"file": "6e00511a-8ac4-4b72-9acc-9d069992b5cf"},
                step_id=step.id,
                exit_stack=inner_stack,
            )
            self.assertEqual(
                result,
                PrepParamsResult(
                    {"file": "6e00511a-8ac4-4b72-9acc-9d069992b5cf"},
                    tab_outputs=[],
                    uploaded_files={
                        "6e00511a-8ac4-4b72-9acc-9d069992b5cf": UploadedFile(
                            "x.csv.gz",
                            "6e00511a-8ac4-4b72-9acc-9d069992b5cf_x.csv.gz",
                            model.created_at,
                        )
                    },
                ),
            )
            self.assertEqual(
                (
                    self.basedir / "6e00511a-8ac4-4b72-9acc-9d069992b5cf_x.csv.gz"
                ).read_bytes(),
                b"1234",
            )

        # Assert that once `exit_stack` goes out of scope, file is deleted
        self.assertFalse(
            (self.basedir / "6e00511a-8ac4-4b72-9acc-9d069992b5cf_x.csv.gz").exists()
        )

    def test_clean_file_safe_filename(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(module_id_name="uploadfile", order=0, slug="step-1")
        key = f"wf-${workflow.id}/wfm-${step.id}/6e00511a-8ac4-4b72-9acc-9d069992b5cf"
        s3.put_bytes(s3.UserFilesBucket, key, b"1234")
        model = UploadedFileModel.objects.create(
            step=step,
            name="/etc/passwd.$/etc/passwd",
            size=4,
            uuid="6e00511a-8ac4-4b72-9acc-9d069992b5cf",
            key=key,
        )
        with ExitStack() as inner_stack:
            result = self._call_prep_params(
                ParamSchema.Dict({"file": ParamSchema.File()}),
                {"file": "6e00511a-8ac4-4b72-9acc-9d069992b5cf"},
                step_id=step.id,
                exit_stack=inner_stack,
            )
            self.assertEqual(
                result.uploaded_files["6e00511a-8ac4-4b72-9acc-9d069992b5cf"],
                UploadedFile(
                    "/etc/passwd.$/etc/passwd",
                    "6e00511a-8ac4-4b72-9acc-9d069992b5cf_-etc-passwd.--etc-passwd",
                    model.created_at,
                ),
            )

    def test_clean_file_no_uploaded_file(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(module_id_name="uploadfile", order=0, slug="step-1")
        result = self._call_clean_value(
            ParamSchema.File(), str(uuid.uuid4()), step_id=step.id
        )
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
        UploadedFileModel.objects.create(
            step=step2, name="x.csv.gz", size=4, uuid=id, key=key
        )
        result = self._call_clean_value(ParamSchema.File(), id, step_id=step.id)
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
        UploadedFileModel.objects.create(
            step=step2, name="x.csv.gz", size=4, uuid=id, key=key
        )
        result = self._call_clean_value(ParamSchema.File(), id, step_id=step.id)
        self.assertIsNone(result)
        # Assert that if a temporary file was created to house the download, it
        # no longer exists.
        self.assertListEqual(list(self.basedir.iterdir()), [])

    def test_clean_normal_dict(self):
        schema = ParamSchema.Dict(
            {"str": ParamSchema.String(), "int": ParamSchema.Integer()}
        )
        value = {"str": "foo", "int": 3}
        expected = dict(value)  # no-op
        result = self._call_clean_value(schema, value)
        self.assertEqual(result, expected)

    def test_clean_column_valid(self):
        result = self._call_clean_value(
            ParamSchema.Column(), "A", input_table_columns=[TEXT("A")]
        )
        self.assertEqual(result, "A")

    def test_clean_column_prompting_error_convert_to_text(self):
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Column(column_types=frozenset({"text"})),
                "A",
                input_table_columns=[NUMBER("A")],
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], None, frozenset({"text"}))],
        )

    def test_clean_column_prompting_error_convert_to_number(self):
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Column(column_types=frozenset({"number"})),
                "A",
                input_table_columns=[TEXT("A")],
            )
        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], "text", frozenset({"number"}))],
        )

    def test_list_prompting_error_concatenate_same_type(self):
        schema = ParamSchema.List(
            inner_schema=ParamSchema.Column(column_types=frozenset({"number"}))
        )
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                schema, ["A", "B"], input_table_columns=[TEXT("A"), TEXT("B")]
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], "text", frozenset({"number"}))],
        )

    def test_list_prompting_error_concatenate_different_type(self):
        schema = ParamSchema.List(
            inner_schema=ParamSchema.Column(column_types=frozenset({"number"}))
        )
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                schema, ["A", "B"], input_table_columns=[TEXT("A"), TIMESTAMP("B")]
            )

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
        schema = ParamSchema.List(
            inner_schema=ParamSchema.Column(column_types=frozenset({"text"}))
        )
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                schema, ["A", "B"], input_table_columns=[NUMBER("A"), TIMESTAMP("B")]
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], None, frozenset({"text"}))],
        )

    def test_dict_prompting_error(self):
        schema = ParamSchema.Dict(
            {
                "col1": ParamSchema.Column(column_types=frozenset({"number"})),
                "col2": ParamSchema.Column(column_types=frozenset({"timestamp"})),
            }
        )
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                schema,
                {"col1": "A", "col2": "B"},
                input_table_columns=[TEXT("A"), TEXT("B")],
            )

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(["B"], "text", frozenset({"timestamp"})),
            ],
        )

    def test_dict_prompting_error_concatenate_same_type(self):
        schema = ParamSchema.Dict(
            {
                "x": ParamSchema.Column(column_types=frozenset({"number"})),
                "y": ParamSchema.Column(column_types=frozenset({"number"})),
            }
        )
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                schema, {"x": "A", "y": "B"}, input_table_columns=[TEXT("A"), TEXT("B")]
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], "text", frozenset({"number"}))],
        )

    def test_dict_prompting_error_concatenate_different_types(self):
        schema = ParamSchema.Dict(
            {
                "x": ParamSchema.Column(column_types=frozenset({"number"})),
                "y": ParamSchema.Column(column_types=frozenset({"number"})),
            }
        )
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                schema,
                {"x": "A", "y": "B"},
                input_table_columns=[TEXT("A"), TIMESTAMP("B")],
            )

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(
                    ["B"], "timestamp", frozenset({"number"})
                ),
            ],
        )

    def test_clean_column_missing_becomes_empty_string(self):  # TODO make it None
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Column(), "B", input_table_columns=[TEXT("A")]
            ),
            "",
        )

    def test_clean_multicolumn_valid(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Multicolumn(),
                ["A", "B"],
                input_table_columns=[TEXT("A"), TEXT("B")],
            ),
            ["A", "B"],
        )

    def test_clean_multicolumn_sort_in_table_order(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Multicolumn(),
                ["A", "B"],
                input_table_columns=[TEXT("B"), TEXT("A")],
            ),
            ["B", "A"],
        )

    def test_clean_multicolumn_prompting_error_convert_to_text(self):
        with self.assertRaises(PromptingError) as cm:
            schema = ParamSchema.Multicolumn(column_types=frozenset({"text"}))
            self._call_clean_value(
                schema,
                ["A", "B"],
                input_table_columns=[NUMBER("A"), TIMESTAMP("B"), TEXT("C")],
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], None, frozenset({"text"}))],
        )

    def test_clean_multicolumn_missing_is_removed(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Multicolumn(),
                ["A", "X", "B"],
                input_table_columns=[TEXT("A"), TEXT("B")],
            ),
            ["A", "B"],
        )

    def test_clean_multichartseries_missing_is_removed(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Multichartseries(),
                [
                    {"column": "A", "color": "#aaaaaa"},
                    {"column": "C", "color": "#cccccc"},
                ],
                input_table_columns=[NUMBER("A"), NUMBER("B")],
            ),
            [{"column": "A", "color": "#aaaaaa"}],
        )

    def test_clean_multichartseries_non_number_is_prompting_error(self):
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Multichartseries(),
                [
                    {"column": "A", "color": "#aaaaaa"},
                    {"column": "B", "color": "#cccccc"},
                ],
                input_table_columns=[TEXT("A"), TIMESTAMP("B")],
            )

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
        result = self._call_prep_params(
            ParamSchema.Dict({"x": ParamSchema.Tab()}),
            {"x": "tab-1"},
            tab_results={
                Tab("tab-1", "Tab 1"): StepResult(Path("tab-1.arrow"), [TEXT("A")])
            },
        )
        self.assertEqual(
            result,
            PrepParamsResult(
                {"x": "tab-1"},
                tab_outputs=[TabOutput("Tab 1", "tab-1.arrow")],
                uploaded_files={},
            ),
        )

    def test_clean_tab_omit_unused_tabs_from_tab_outputs(self):
        result = self._call_prep_params(
            ParamSchema.Dict({"x": ParamSchema.Tab()}),
            {"x": "tab-1"},
            tab_results={
                Tab("tab-1", "Tab 1"): StepResult(Path("tab-1.arrow"), [TEXT("A")]),
                Tab("tab-2", "Tab 2"): StepResult(Path("tab-2.arrow"), [TEXT("A")]),
                Tab("tab-3", "Tab 3"): StepResult(Path("tab-3.arrow"), [TEXT("A")]),
            },
        )
        self.assertEqual(result.tab_outputs, [TabOutput("Tab 1", "tab-1.arrow")])

    def test_clean_multicolumn_from_other_tab(self):
        schema = ParamSchema.Dict(
            {
                "tab": ParamSchema.Tab(),
                "columns": ParamSchema.Multicolumn(tab_parameter="tab"),
            }
        )
        params = {"tab": "tab-2", "columns": ["A-from-tab-1", "A-from-tab-2"]}
        result = self._call_prep_params(
            schema,
            params,
            input_table_columns=[NUMBER("A-from-tab-1")],
            tab_results={
                Tab("tab-2", "Tab 2"): StepResult(
                    Path("tab-2.arrow"), [NUMBER("A-from-tab-2")]
                )
            },
        )
        self.assertEqual(result.params["columns"], ["A-from-tab-2"])

    def test_clean_multicolumn_from_other_tab_that_does_not_exist(self):
        # The other tab would not exist if the user selected and then deleted
        # it.
        result = self._call_prep_params(
            schema=ParamSchema.Dict(
                {
                    "tab": ParamSchema.Tab(),
                    "columns": ParamSchema.Multicolumn(tab_parameter="tab"),
                }
            ),
            params={"tab": "tab-missing", "columns": ["A-from-tab-1"]},
            input_table_columns=[NUMBER("A-from-tab-1")],
            tab_results={},
        )
        # result.params['tab'] is not what we're testing here
        self.assertEqual(result.params["columns"], [])

    def test_clean_tab_no_tab_selected_gives_none(self):
        self.assertIsNone(self._call_clean_value(ParamSchema.Tab(), ""))

    def test_clean_tab_missing_tab_selected_gives_none(self):
        # If the user has selected a nonexistent tab, pretend tab is blank.
        #
        # JS sees nonexistent tab slugs. render() doesn't.
        self.assertIsNone(self._call_clean_value(ParamSchema.Tab(), "tab-XXX"))

    def test_clean_tab_cycle(self):
        tab = Tab("tab-1", "Tab 1")
        with self.assertRaises(TabCycleError):
            self._call_clean_value(ParamSchema.Tab(), "tab-1", tab_results={tab: None})

    def test_clean_tab_unreachable(self):
        tab = Tab("tab-error", "Buggy Tab")
        with self.assertRaises(TabOutputUnreachableError):
            self._call_clean_value(
                ParamSchema.Tab(),
                "tab-error",
                tab_results={tab: StepResult(Path("tab-error.arrow"), [])},
            )

    def test_clean_tabs_happy_path(self):
        tab_results = {
            Tab("tab-2", "Tab 2"): StepResult(Path("tab-2.arrow"), [NUMBER("B")]),
            Tab("tab-3", "Tab 3"): StepResult(Path("tab-3.arrow"), [NUMBER("C")]),
        }
        self.assertEqual(
            self._call_prep_params(
                ParamSchema.Dict({"x": ParamSchema.Multitab()}),
                {"x": ["tab-2", "tab-3"]},
                tab_results=tab_results,
            ),
            PrepParamsResult(
                {"x": ["tab-2", "tab-3"]},
                [TabOutput("tab-2", "tab-2.arrow"), TabOutput("tab-3", "tab-3.arrow")],
                uploaded_files={},
            ),
        )

    def test_clean_tabs_preserve_ordering(self):
        # "x" gives wrongly-ordered tabs; renderprep should reorder them.
        result = self._call_prep_params(
            ParamSchema.Dict({"x": ParamSchema.Multitab()}),
            {"x": ["tab-2", "tab-3"]},
            tab_results={
                Tab("tab-3", "Tab 3"): StepResult(Path("tab-3.arrow"), [NUMBER("C")]),
                Tab("tab-2", "Tab 2"): StepResult(Path("tab-2.arrow"), [NUMBER("B")]),
            },
        )
        self.assertEqual(
            result,
            PrepParamsResult(
                {"x": ["tab-3", "tab-2"]},
                [TabOutput("tab-3", "tab-3.arrow"), TabOutput("tab-2", "tab-2.arrow")],
                uploaded_files={},
            ),
        )

    def test_clean_tabs_nix_missing_tab(self):
        self.assertEqual(
            self._call_clean_value(ParamSchema.Multitab(), ["tab-missing"]), []
        )

    def test_clean_tabs_tab_cycle(self):
        with self.assertRaises(TabCycleError):
            self._call_clean_value(
                ParamSchema.Multitab(),
                ["tab-1"],
                tab_results={Tab("tab-1", "Tab 1"): None},
            )

    def test_clean_tabs_tab_unreachable(self):
        with self.assertRaises(TabOutputUnreachableError):
            self._call_clean_value(
                ParamSchema.Multitab(),
                ["tab-1"],
                tab_results={
                    Tab("tab-1", "Tab 1"): StepResult(Path("tab-1.arrow"), [])
                },
            )

    def test_clean_condition_empty_and_and_or_are_none(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": []}],
                },
                input_table_columns=[NUMBER("A")],
            ),
            None,
        )

    def test_clean_condition_empty_column_is_none(self):
        self.assertIsNone(
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "text_is",
                    "column": "",
                    "value": "",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
            )
        )
        # And test it in the context of a broader and/or
        self.assertIsNone(
            self._call_clean_value(
                ParamSchema.Condition(),
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
                input_table_columns=[NUMBER("A")],
            )
        )

    def test_clean_condition_and_or_simplify(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Condition(),
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
                input_table_columns=[NUMBER("A")],
            ),
            {
                "operation": "cell_is_blank",
                "column": "A",
            },
        )

    def test_clean_condition_and_or_multiple_conditions(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Condition(),
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
                input_table_columns=[TEXT("A")],
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
        self.assertIsNone(
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "text_is",
                    "column": "B",
                    "value": "",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
            )
        )

    def test_clean_condition_text_wrong_type(self):
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "text_is",
                    "column": "A",
                    "value": "",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], None, frozenset({"text"}))],
        )

    def test_clean_condition_text_happy_path(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "text_is",
                    "column": "A",
                    "value": "a",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[TEXT("A")],
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
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "text_is_not",
                    "column": "A",
                    "value": "a",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[TEXT("A")],
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
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "text_is",
                    "column": "A",
                    "value": "",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], None, frozenset({"text"}))],
        )

    def test_clean_condition_number_wrong_column_type(self):
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "number_is",
                    "column": "A",
                    "value": "1",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[TEXT("A")],
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], "text", frozenset({"number"}))],
        )

    def test_clean_condition_number_wrong_value(self):
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "number_is",
                    "column": "A",
                    "value": "bad",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
            )

        self.assertEqual(
            cm.exception.errors, [PromptingError.CannotCoerceValueToNumber("bad")]
        )

    def test_clean_condition_number_wrong_column_type_and_wrong_value(self):
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "number_is",
                    "column": "A",
                    "value": "bad",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[TEXT("A")],
            )

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.CannotCoerceValueToNumber("bad"),
            ],
        )

    def test_clean_condition_number_happy_path(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "number_is",
                    "column": "A",
                    "value": "1",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
            ),
            {
                "operation": "number_is",
                "column": "A",
                "value": 1,
            },
        )

    def test_clean_condition_timestamp_wrong_column_type(self):
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "timestamp_is_greater_than",
                    "column": "A",
                    "value": "2020-01-01T00:00Z",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
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
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "timestamp_is_greater_than",
                    "column": "A",
                    "value": "Yesterday",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[TIMESTAMP("A")],
            )

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.CannotCoerceValueToTimestamp("Yesterday"),
            ],
        )

    def test_clean_condition_timestamp_wrong_column_type_and_wrong_value(self):
        with self.assertRaises(PromptingError) as cm:
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "timestamp_is_greater_than",
                    "column": "A",
                    "value": "Yesterday",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
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
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "timestamp_is_greater_than",
                    "column": "A",
                    "value": "2020-11-01",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[TIMESTAMP("A")],
            ),
            {
                "operation": "timestamp_is_greater_than",
                "column": "A",
                "value": "2020-11-01",
            },
        )

    def test_clean_condition_untyped(self):
        self.assertEqual(
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "cell_is_blank",
                    "column": "A",
                    "value": "2020-11-01",
                    "isCaseSensitive": True,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
            ),
            {
                "operation": "cell_is_blank",
                "column": "A",
            },
        )

    def test_clean_condition_no_operation(self):
        self.assertIsNone(
            self._call_clean_value(
                ParamSchema.Condition(),
                {
                    "operation": "",
                    "column": "A",
                    "value": "foo",
                    "isCaseSensitive": False,
                    "isRegex": False,
                },
                input_table_columns=[NUMBER("A")],
            )
        )
