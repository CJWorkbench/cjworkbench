import tempfile
import unittest
from pathlib import Path

from cjwkernel import types
from cjwkernel.thrift import ttypes


class ThriftConvertersTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.basedir = Path(tempfile.mkdtemp())

    def tearDown(self):
        self.basedir.rmdir()
        super().tearDown()

    def test_column_type_text_to_thrift(self):
        self.assertEqual(
            types.arrow_column_type_to_thrift(types.ColumnType.Text()),
            ttypes.ColumnType(text_type=ttypes.ColumnTypeText()),
        )

    def test_column_type_text_from_thrift(self):
        self.assertEqual(
            types.thrift_column_type_to_arrow(
                ttypes.ColumnType(text_type=ttypes.ColumnTypeText())
            ),
            types.ColumnType.Text(),
        )

    def test_column_type_number_to_thrift(self):
        self.assertEqual(
            types.arrow_column_type_to_thrift(types.ColumnType.Number("{:,.1%}")),
            ttypes.ColumnType(number_type=ttypes.ColumnTypeNumber("{:,.1%}")),
        )

    def test_column_type_number_from_thrift(self):
        self.assertEqual(
            types.thrift_column_type_to_arrow(
                ttypes.ColumnType(number_type=ttypes.ColumnTypeNumber("{:,.1%}"))
            ),
            types.ColumnType.Number("{:,.1%}"),
        )

    def test_column_type_number_from_thrift_invalid_format(self):
        thrift_value = ttypes.ColumnType(number_type=ttypes.ColumnTypeNumber("{:T}"))
        with self.assertRaisesRegex(ValueError, "Unknown format code 'T'"):
            types.thrift_column_type_to_arrow(thrift_value)

    def test_column_type_timestamp_to_thrift(self):
        self.assertEqual(
            types.arrow_column_type_to_thrift(types.ColumnType.Timestamp()),
            ttypes.ColumnType(timestamp_type=ttypes.ColumnTypeTimestamp()),
        )

    def test_column_type_timestamp_from_thrift(self):
        self.assertEqual(
            types.thrift_column_type_to_arrow(
                ttypes.ColumnType(timestamp_type=ttypes.ColumnTypeTimestamp())
            ),
            types.ColumnType.Timestamp(),
        )

    def test_column_to_thrift(self):
        self.assertEqual(
            types.arrow_column_to_thrift(types.Column("A", types.ColumnType.Text())),
            ttypes.Column("A", ttypes.ColumnType(text_type=ttypes.ColumnTypeText())),
        )

    def test_column_from_thrift(self):
        self.assertEqual(
            types.thrift_column_to_arrow(
                ttypes.Column("A", ttypes.ColumnType(text_type=ttypes.ColumnTypeText()))
            ),
            types.Column("A", types.ColumnType.Text()),
        )

    def test_table_metadata_to_thrift(self):
        self.assertEqual(
            types.arrow_table_metadata_to_thrift(
                types.TableMetadata(
                    4,
                    [
                        types.Column("A", types.ColumnType.Text()),
                        types.Column("B", types.ColumnType.Text()),
                    ],
                )
            ),
            ttypes.TableMetadata(
                4,
                [
                    ttypes.Column(
                        "A", ttypes.ColumnType(text_type=ttypes.ColumnTypeText())
                    ),
                    ttypes.Column(
                        "B", ttypes.ColumnType(text_type=ttypes.ColumnTypeText())
                    ),
                ],
            ),
        )

    def test_table_metadata_from_thrift(self):
        self.assertEqual(
            types.thrift_table_metadata_to_arrow(
                ttypes.TableMetadata(
                    4,
                    [
                        ttypes.Column(
                            "A", ttypes.ColumnType(text_type=ttypes.ColumnTypeText())
                        ),
                        ttypes.Column(
                            "B", ttypes.ColumnType(text_type=ttypes.ColumnTypeText())
                        ),
                    ],
                )
            ),
            types.TableMetadata(
                4,
                [
                    types.Column("A", types.ColumnType.Text()),
                    types.Column("B", types.ColumnType.Text()),
                ],
            ),
        )

    def test_arrow_table_to_thrift(self):
        pass  # TODO test ArrowTable conversions

    def test_arrow_table_from_thrift(self):
        pass  # TODO test ArrowTable conversions
        # ... we should also test _validation_ when reading from thrift.

    def test_tab_to_thrift(self):
        self.assertEqual(
            types.arrow_tab_to_thrift(types.Tab("tab-123", "Tab 1")),
            ttypes.Tab("tab-123", "Tab 1"),
        )

    def test_tab_from_thrift(self):
        self.assertEqual(
            types.thrift_tab_to_arrow(ttypes.Tab("tab-123", "Tab 1")),
            types.Tab("tab-123", "Tab 1"),
        )

    def test_tab_output_from_thrift(self):
        pass  # TODO test ArrowTable conversions, then test TabOutput conversions

    def test_tab_output_to_thrift(self):
        pass  # TODO test ArrowTable conversions, then test TabOutput conversions

    def test_raw_params_from_thrift(self):
        self.assertEqual(
            types.thrift_raw_params_to_arrow(ttypes.RawParams('{"A":"x","B":[1,2]}')),
            types.RawParams({"A": "x", "B": [1, 2]}),
        )

    def test_raw_params_to_thrift(self):
        self.assertEqual(
            types.arrow_raw_params_to_thrift(types.RawParams({"A": "x", "B": [1, 2]})),
            ttypes.RawParams('{"A":"x","B":[1,2]}'),
        )

    def test_params_from_thrift(self):
        self.assertEqual(
            types.thrift_params_to_arrow(
                {
                    "str": ttypes.ParamValue(string_value="s"),
                    "int": ttypes.ParamValue(integer_value=2),
                    "float": ttypes.ParamValue(float_value=1.2),
                    "null": ttypes.ParamValue(),
                    "bool": ttypes.ParamValue(boolean_value=False),
                    "column": ttypes.ParamValue(
                        column_value=ttypes.Column(
                            "A",
                            ttypes.ColumnType(
                                number_type=ttypes.ColumnTypeNumber(format="{:,.2f}")
                            ),
                        )
                    ),
                    "listofmaps": ttypes.ParamValue(
                        list_value=[
                            ttypes.ParamValue(
                                map_value={
                                    "A": ttypes.ParamValue(string_value="a"),
                                    "B": ttypes.ParamValue(string_value="b"),
                                }
                            ),
                            ttypes.ParamValue(
                                map_value={
                                    "C": ttypes.ParamValue(string_value="c"),
                                    "D": ttypes.ParamValue(string_value="d"),
                                }
                            ),
                        ]
                    ),
                    "tab": ttypes.ParamValue(string_value="TODO tabs"),
                },
                self.basedir,
            ),
            types.Params(
                {
                    "str": "s",
                    "int": 2,
                    "float": 1.2,
                    "null": None,
                    "bool": False,
                    "column": types.Column(
                        "A", types.ColumnType.Number(format="{:,.2f}")
                    ),
                    "listofmaps": [{"A": "a", "B": "b"}, {"C": "c", "D": "d"}],
                    "tab": "TODO tabs",
                }
            ),
        )

    def test_params_to_thrift(self):
        self.assertEqual(
            types.arrow_params_to_thrift(
                types.Params(
                    {
                        "str": "s",
                        "int": 2,
                        "float": 1.2,
                        "null": None,
                        "bool": False,
                        "column": types.Column(
                            "A", types.ColumnType.Number(format="{:,.2f}")
                        ),
                        "listofmaps": [{"A": "a", "B": "b"}, {"C": "c", "D": "d"}],
                        "tab": "TODO tabs",
                    }
                )
            ),
            {
                "str": ttypes.ParamValue(string_value="s"),
                "int": ttypes.ParamValue(integer_value=2),
                "float": ttypes.ParamValue(float_value=1.2),
                "null": ttypes.ParamValue(),
                "bool": ttypes.ParamValue(boolean_value=False),
                "column": ttypes.ParamValue(
                    column_value=ttypes.Column(
                        "A",
                        ttypes.ColumnType(
                            number_type=ttypes.ColumnTypeNumber(format="{:,.2f}")
                        ),
                    )
                ),
                "listofmaps": ttypes.ParamValue(
                    list_value=[
                        ttypes.ParamValue(
                            map_value={
                                "A": ttypes.ParamValue(string_value="a"),
                                "B": ttypes.ParamValue(string_value="b"),
                            }
                        ),
                        ttypes.ParamValue(
                            map_value={
                                "C": ttypes.ParamValue(string_value="c"),
                                "D": ttypes.ParamValue(string_value="d"),
                            }
                        ),
                    ]
                ),
                "tab": ttypes.ParamValue(string_value="TODO tabs"),
            },
        )

    def test_params_filename_from_thrift_happy_path(self):
        with tempfile.NamedTemporaryFile(dir=self.basedir) as tf:
            path = Path(tf.name)
            path.write_bytes(b"")
            self.assertEqual(
                types.thrift_params_to_arrow(
                    {"A": ttypes.ParamValue(filename_value=path.name)}, self.basedir
                ),
                types.Params({"A": path}),
            )

    def test_params_filename_to_thrift(self):
        path = self.basedir / "x.bin"
        self.assertEqual(
            types.arrow_params_to_thrift(types.Params({"A": path})),
            {"A": ttypes.ParamValue(filename_value="x.bin")},
        )

    def test_params_filename_from_thrift_file_not_found_is_error(self):
        with self.assertRaisesRegexp(ValueError, "file must exist"):
            types.thrift_params_to_arrow(
                {"A": ttypes.ParamValue(filename_value="does_not_exist")}, self.basedir
            )

    def test_i18n_message_from_thrift_source_module(self):
        self.assertEqual(
            types.thrift_i18n_message_to_arrow(
                ttypes.I18nMessage(
                    "modules.x.y",
                    {
                        "a": ttypes.I18nArgument(string_value="s"),
                        "b": ttypes.I18nArgument(i32_value=12345678),
                        "c": ttypes.I18nArgument(double_value=0.123),
                    },
                    "module",
                )
            ),
            types.I18nMessage(
                "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "module"
            ),
        )

    def test_i18n_message_to_thrift_source_module(self):
        self.assertEqual(
            types.arrow_i18n_message_to_thrift(
                types.I18nMessage(
                    "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "module"
                )
            ),
            ttypes.I18nMessage(
                "modules.x.y",
                {
                    "a": ttypes.I18nArgument(string_value="s"),
                    "b": ttypes.I18nArgument(i32_value=12345678),
                    "c": ttypes.I18nArgument(double_value=0.123),
                },
                "module",
            ),
        )

    def test_i18n_message_from_thrift_source_library(self):
        self.assertEqual(
            types.thrift_i18n_message_to_arrow(
                ttypes.I18nMessage(
                    "modules.x.y",
                    {
                        "a": ttypes.I18nArgument(string_value="s"),
                        "b": ttypes.I18nArgument(i32_value=12345678),
                        "c": ttypes.I18nArgument(double_value=0.123),
                    },
                    "cjwmodule",
                )
            ),
            types.I18nMessage(
                "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "cjwmodule"
            ),
        )

    def test_i18n_message_to_thrift_source_library(self):
        self.assertEqual(
            types.arrow_i18n_message_to_thrift(
                types.I18nMessage(
                    "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "cjwmodule"
                )
            ),
            ttypes.I18nMessage(
                "modules.x.y",
                {
                    "a": ttypes.I18nArgument(string_value="s"),
                    "b": ttypes.I18nArgument(i32_value=12345678),
                    "c": ttypes.I18nArgument(double_value=0.123),
                },
                "cjwmodule",
            ),
        )

    def test_i18n_message_from_thrift_source_none(self):
        self.assertEqual(
            types.thrift_i18n_message_to_arrow(
                ttypes.I18nMessage(
                    "modules.x.y",
                    {
                        "a": ttypes.I18nArgument(string_value="s"),
                        "b": ttypes.I18nArgument(i32_value=12345678),
                        "c": ttypes.I18nArgument(double_value=0.123),
                    },
                    None,
                )
            ),
            types.I18nMessage("modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}),
        )

    def test_i18n_message_to_thrift_source_none(self):
        self.assertEqual(
            types.arrow_i18n_message_to_thrift(types.I18nMessage("modules.x.y")),
            ttypes.I18nMessage("modules.x.y", {}, None),
        )

    def test_i18n_message_from_thrift_invalid_source(self):
        with self.assertRaises(ValueError):
            types.thrift_i18n_message_to_arrow(
                ttypes.I18nMessage("modules.x.y", {}, "random")
            )

    def test_prepend_step_quick_fix_action_from_thrift(self):
        self.assertEqual(
            types.thrift_quick_fix_action_to_arrow(
                ttypes.QuickFixAction(
                    prepend_step=ttypes.PrependStepQuickFixAction(
                        "filter", ttypes.RawParams('{"x":"y"}')
                    )
                )
            ),
            types.QuickFixAction.PrependStep("filter", {"x": "y"}),
        )

    def test_prepend_step_quick_fix_action_to_thrift(self):
        self.assertEqual(
            types.arrow_quick_fix_action_to_thrift(
                types.QuickFixAction.PrependStep("filter", {"x": "y"})
            ),
            ttypes.QuickFixAction(
                prepend_step=ttypes.PrependStepQuickFixAction(
                    "filter", ttypes.RawParams('{"x":"y"}')
                )
            ),
        )

    def test_quick_fix_from_thrift(self):
        self.assertEqual(
            types.thrift_quick_fix_to_arrow(
                ttypes.QuickFix(
                    ttypes.I18nMessage("click", {}, None),
                    ttypes.QuickFixAction(
                        prepend_step=ttypes.PrependStepQuickFixAction(
                            "filter", ttypes.RawParams('{"x":"y"}')
                        )
                    ),
                )
            ),
            types.QuickFix(
                types.I18nMessage("click"),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ),
        )

    def test_quick_fix_to_thrift(self):
        self.assertEqual(
            types.arrow_quick_fix_to_thrift(
                types.QuickFix(
                    types.I18nMessage("click"),
                    types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                )
            ),
            ttypes.QuickFix(
                ttypes.I18nMessage("click", {}, None),
                ttypes.QuickFixAction(
                    prepend_step=ttypes.PrependStepQuickFixAction(
                        "filter", ttypes.RawParams('{"x":"y"}')
                    )
                ),
            ),
        )

    def test_render_error_from_thrift(self):
        self.assertEqual(
            types.thrift_render_error_to_arrow(
                ttypes.RenderError(
                    ttypes.I18nMessage("foo", {}, None),
                    [
                        ttypes.QuickFix(
                            ttypes.I18nMessage("click", {}, None),
                            ttypes.QuickFixAction(
                                prepend_step=ttypes.PrependStepQuickFixAction(
                                    "filter", ttypes.RawParams('{"x":"y"}')
                                )
                            ),
                        )
                    ],
                )
            ),
            types.RenderError(
                types.I18nMessage("foo", {}),
                [
                    types.QuickFix(
                        types.I18nMessage("click"),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ),
        )

    def test_render_error_to_thrift(self):
        self.assertEqual(
            types.arrow_render_error_to_thrift(
                types.RenderError(
                    types.I18nMessage("foo", {}),
                    [
                        types.QuickFix(
                            types.I18nMessage("click"),
                            types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                        )
                    ],
                )
            ),
            ttypes.RenderError(
                ttypes.I18nMessage("foo", {}, None),
                [
                    ttypes.QuickFix(
                        ttypes.I18nMessage("click", {}, None),
                        ttypes.QuickFixAction(
                            prepend_step=ttypes.PrependStepQuickFixAction(
                                "filter", ttypes.RawParams('{"x":"y"}')
                            )
                        ),
                    )
                ],
            ),
        )

    def test_render_result_from_thrift(self):
        pass  # TODO test RenderResult conversion

    def test_render_result_to_thrift(self):
        pass  # TODO test RenderResult conversion

    def test_fetch_result_from_thrift_disallow_directories(self):
        with self.assertRaisesRegex(ValueError, "must not contain directories"):
            types.thrift_fetch_result_to_arrow(
                ttypes.FetchResult("/etc/passwd", []), Path(__file__).parent
            )

    def test_fetch_result_from_thrift_disallow_hidden_files(self):
        with self.assertRaisesRegex(ValueError, "must not be hidden"):
            types.thrift_fetch_result_to_arrow(
                ttypes.FetchResult(".secrets", []), Path(__file__).parent
            )

    def test_fetch_result_from_thrift_disallow_non_files(self):
        with self.assertRaisesRegex(ValueError, "must exist"):
            types.thrift_fetch_result_to_arrow(
                ttypes.FetchResult("missing", []), self.basedir
            )

    def test_fetch_result_from_thrift_disallow_non_file(self):
        with tempfile.TemporaryDirectory(dir=str(self.basedir)) as tmpsubdir:
            with self.assertRaisesRegex(ValueError, "be a regular file"):
                types.thrift_fetch_result_to_arrow(
                    ttypes.FetchResult(Path(tmpsubdir).name, []), self.basedir
                )

    def test_fetch_result_from_thrift_happy_path(self):
        with tempfile.NamedTemporaryFile(dir=str(self.basedir)) as tf:
            self.assertEqual(
                types.thrift_fetch_result_to_arrow(
                    ttypes.FetchResult(
                        Path(tf.name).name,
                        [ttypes.RenderError(ttypes.I18nMessage("hi", {}), [])],
                    ),
                    self.basedir,
                ),
                types.FetchResult(
                    Path(tf.name), [types.RenderError(types.I18nMessage("hi"))]
                ),
            )
