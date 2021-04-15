import os
import tempfile
import unittest
from pathlib import Path

from cjwkernel import types
from cjwkernel.thrift import ttypes
from cjwmodule.i18n import I18nMessage


class ColumnTypeNumberTests(unittest.TestCase):
    def test_format_too_many_arguments(self):
        with self.assertRaisesRegex(ValueError, "Can only format one number"):
            types.parse_number_format("{:d}{:f}")

    def test_format_disallow_non_format(self):
        with self.assertRaisesRegex(ValueError, 'Format must look like "{:...}"'):
            types.parse_number_format("%d")

    def test_format_disallow_field_number(self):
        with self.assertRaisesRegex(
            ValueError, "Field names or numbers are not allowed"
        ):
            types.parse_number_format("{0:f}")

    def test_format_disallow_field_name(self):
        with self.assertRaisesRegex(
            ValueError, "Field names or numbers are not allowed"
        ):
            types.parse_number_format("{value:f}")

    def test_format_disallow_field_converter(self):
        with self.assertRaisesRegex(ValueError, "Field converters are not allowed"):
            types.parse_number_format("{!r:f}")

    def test_format_disallow_invalid_type(self):
        with self.assertRaisesRegex(ValueError, "Unknown format code 'T'"):
            types.parse_number_format("{:T}")


class ThriftConvertersTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.basedir = Path(tempfile.mkdtemp())
        self.old_cwd = os.getcwd()
        os.chdir(self.basedir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.basedir.rmdir()
        super().tearDown()

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
            filename = Path(tf.name).name
            Path(tf.name).write_bytes(b"")
            self.assertEqual(
                types.thrift_params_to_arrow(
                    {"A": ttypes.ParamValue(filename_value=filename)}, self.basedir
                ),
                types.Params({"A": Path(tf.name)}),
            )

    def test_params_filename_to_thrift(self):
        self.assertEqual(
            types.arrow_params_to_thrift(types.Params({"A": Path("x.bin")})),
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
            I18nMessage("modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "module"),
        )

    def test_i18n_message_to_thrift_source_module(self):
        self.assertEqual(
            types.arrow_i18n_message_to_thrift(
                I18nMessage(
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
            I18nMessage(
                "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "cjwmodule"
            ),
        )

    def test_i18n_message_to_thrift_source_library(self):
        self.assertEqual(
            types.arrow_i18n_message_to_thrift(
                I18nMessage(
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
            I18nMessage("modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, None),
        )

    def test_i18n_message_to_thrift_source_none(self):
        self.assertEqual(
            types.arrow_i18n_message_to_thrift(I18nMessage("modules.x.y", {}, None)),
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
                I18nMessage("click", {}, None),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ),
        )

    def test_quick_fix_to_thrift(self):
        self.assertEqual(
            types.arrow_quick_fix_to_thrift(
                types.QuickFix(
                    I18nMessage("click", {}, None),
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
                I18nMessage("foo", {}, None),
                [
                    types.QuickFix(
                        I18nMessage("click", {}, None),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ),
        )

    def test_render_error_to_thrift(self):
        self.assertEqual(
            types.arrow_render_error_to_thrift(
                types.RenderError(
                    I18nMessage("foo", {}, None),
                    [
                        types.QuickFix(
                            I18nMessage("click", {}, None),
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
        with self.assertRaisesRegex(ValueError, "must not include directory names"):
            types.thrift_fetch_result_to_arrow(
                ttypes.FetchResult("/etc/passwd", []), self.basedir
            )

    def test_fetch_result_from_thrift_disallow_hidden_files(self):
        with self.assertRaisesRegex(ValueError, "must not be hidden"):
            types.thrift_fetch_result_to_arrow(
                ttypes.FetchResult(".secrets", []), self.basedir
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
                    ttypes.FetchResult(Path(tmpsubdir).name, []),
                    self.basedir,
                )

    def test_fetch_result_from_thrift_happy_path(self):
        with tempfile.NamedTemporaryFile(dir=str(self.basedir)) as tf:
            filename = Path(tf.name).name
            self.assertEqual(
                types.thrift_fetch_result_to_arrow(
                    ttypes.FetchResult(
                        filename,
                        [ttypes.RenderError(ttypes.I18nMessage("hi", {}, None), [])],
                    ),
                    self.basedir,
                ),
                types.FetchResult(
                    Path(tf.name),
                    [types.RenderError(types.I18nMessage("hi", {}, None))],
                ),
            )
