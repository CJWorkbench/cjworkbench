from pathlib import Path
import tempfile
import unittest
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
            types.ColumnType.Text().to_thrift(),
            ttypes.ColumnType(text_type=ttypes.ColumnTypeText()),
        )

    def test_column_type_text_from_thrift(self):
        self.assertEqual(
            types.ColumnType.from_thrift(
                ttypes.ColumnType(text_type=ttypes.ColumnTypeText())
            ),
            types.ColumnType.Text(),
        )

    def test_column_type_number_to_thrift(self):
        self.assertEqual(
            types.ColumnType.Number("{:,.1%}").to_thrift(),
            ttypes.ColumnType(number_type=ttypes.ColumnTypeNumber("{:,.1%}")),
        )

    def test_column_type_number_from_thrift(self):
        self.assertEqual(
            types.ColumnType.from_thrift(
                ttypes.ColumnType(number_type=ttypes.ColumnTypeNumber("{:,.1%}"))
            ),
            types.ColumnType.Number("{:,.1%}"),
        )

    def test_column_type_number_from_thrift_invalid_format(self):
        thrift_value = ttypes.ColumnType(number_type=ttypes.ColumnTypeNumber("{:T}"))
        with self.assertRaisesRegex(ValueError, "Unknown format code 'T'"):
            types.ColumnType.from_thrift(thrift_value)

    def test_column_type_datetime_to_thrift(self):
        self.assertEqual(
            types.ColumnType.Datetime().to_thrift(),
            ttypes.ColumnType(datetime_type=ttypes.ColumnTypeDatetime()),
        )

    def test_column_type_datetime_from_thrift(self):
        self.assertEqual(
            types.ColumnType.from_thrift(
                ttypes.ColumnType(datetime_type=ttypes.ColumnTypeDatetime())
            ),
            types.ColumnType.Datetime(),
        )

    def test_column_to_thrift(self):
        self.assertEqual(
            types.Column("A", types.ColumnType.Text()).to_thrift(),
            ttypes.Column("A", ttypes.ColumnType(text_type=ttypes.ColumnTypeText())),
        )

    def test_column_from_thrift(self):
        self.assertEqual(
            types.Column.from_thrift(
                ttypes.Column("A", ttypes.ColumnType(text_type=ttypes.ColumnTypeText()))
            ),
            types.Column("A", types.ColumnType.Text()),
        )

    def test_table_metadata_to_thrift(self):
        self.assertEqual(
            types.TableMetadata(
                4,
                [
                    types.Column("A", types.ColumnType.Text()),
                    types.Column("B", types.ColumnType.Text()),
                ],
            ).to_thrift(),
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
            types.TableMetadata.from_thrift(
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
            types.Tab("tab-123", "Tab 1").to_thrift(), ttypes.Tab("tab-123", "Tab 1")
        )

    def test_tab_from_thrift(self):
        self.assertEqual(
            types.Tab.from_thrift(ttypes.Tab("tab-123", "Tab 1")),
            types.Tab("tab-123", "Tab 1"),
        )

    def test_tab_output_from_thrift(self):
        pass  # TODO test ArrowTable conversions, then test TabOutput conversions

    def test_tab_output_to_thrift(self):
        pass  # TODO test ArrowTable conversions, then test TabOutput conversions

    def test_raw_params_from_thrift(self):
        self.assertEqual(
            types.RawParams.from_thrift(ttypes.RawParams('{"A":"x","B":[1,2]}')),
            types.RawParams({"A": "x", "B": [1, 2]}),
        )

    def test_raw_params_to_thrift(self):
        self.assertEqual(
            types.RawParams({"A": "x", "B": [1, 2]}).to_thrift(),
            ttypes.RawParams('{"A":"x","B":[1,2]}'),
        )

    def test_params_from_thrift(self):
        self.assertEqual(
            types.Params.from_thrift(
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
            ).to_thrift(),
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
                types.Params.from_thrift(
                    {"A": ttypes.ParamValue(filename_value=path.name)}, self.basedir
                ),
                types.Params({"A": path}),
            )

    def test_params_filename_to_thrift(self):
        path = self.basedir / "x.bin"
        self.assertEqual(
            types.Params({"A": path}).to_thrift(),
            {"A": ttypes.ParamValue(filename_value="x.bin")},
        )

    def test_params_filename_from_thrift_file_not_found_is_error(self):
        with self.assertRaisesRegexp(ValueError, "file must exist"):
            types.Params.from_thrift(
                {"A": ttypes.ParamValue(filename_value="does_not_exist")}, self.basedir
            )

    def test_i18n_message_from_thrift_source_module(self):
        self.assertEqual(
            types.I18nMessage.from_thrift(
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
            types.I18nMessage(
                "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "module"
            ).to_thrift(),
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
            types.I18nMessage.from_thrift(
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
            types.I18nMessage(
                "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "cjwmodule"
            ).to_thrift(),
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
            types.I18nMessage.from_thrift(
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
            types.I18nMessage(
                "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}
            ).to_thrift(),
            ttypes.I18nMessage(
                "modules.x.y",
                {
                    "a": ttypes.I18nArgument(string_value="s"),
                    "b": ttypes.I18nArgument(i32_value=12345678),
                    "c": ttypes.I18nArgument(double_value=0.123),
                },
                None,
            ),
        )

    def test_i18n_message_from_dict_source_library(self):
        self.assertEqual(
            types.I18nMessage.from_dict(
                {
                    "id": "modules.x.y",
                    "arguments": ["s", 12345678, 0.123],
                    "source": "cjwmodule",
                }
            ),
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123], "cjwmodule"),
        )

    def test_i18n_message_to_dict_source_library(self):
        self.assertEqual(
            types.I18nMessage(
                "modules.x.y", ["s", 12345678, 0.123], "cjwmodule"
            ).to_dict(),
            {
                "id": "modules.x.y",
                "arguments": ["s", 12345678, 0.123],
                "source": "cjwmodule",
            },
        )

    def test_i18n_message_from_dict_source_module(self):
        self.assertEqual(
            types.I18nMessage.from_dict(
                {
                    "id": "modules.x.y",
                    "arguments": ["s", 12345678, 0.123],
                    "source": "module",
                }
            ),
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123], "module"),
        )

    def test_i18n_message_to_dict_source_module(self):
        self.assertEqual(
            types.I18nMessage(
                "modules.x.y", ["s", 12345678, 0.123], "module"
            ).to_dict(),
            {
                "id": "modules.x.y",
                "arguments": ["s", 12345678, 0.123],
                "source": "module",
            },
        )

    def test_i18n_message_from_dict_no_source(self):
        self.assertEqual(
            types.I18nMessage.from_dict(
                {"id": "modules.x.y", "arguments": ["s", 12345678, 0.123]}
            ),
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123]),
        )

    def test_i18n_message_to_dict_no_source(self):
        self.assertEqual(
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123]).to_dict(),
            {"id": "modules.x.y", "arguments": ["s", 12345678, 0.123]},
        )

    def test_prepend_step_quick_fix_action_from_thrift(self):
        self.assertEqual(
            types.QuickFixAction.from_thrift(
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
            types.QuickFixAction.PrependStep("filter", {"x": "y"}).to_thrift(),
            ttypes.QuickFixAction(
                prepend_step=ttypes.PrependStepQuickFixAction(
                    "filter", ttypes.RawParams('{"x":"y"}')
                )
            ),
        )

    def test_prepend_step_quick_fix_action_from_dict(self):
        self.assertEqual(
            types.QuickFixAction.from_dict(
                {
                    "type": "prependStep",
                    "moduleSlug": "filter",
                    "partialParams": {"x": "y"},
                }
            ),
            types.QuickFixAction.PrependStep("filter", {"x": "y"}),
        )

    def test_prepend_step_quick_fix_action_to_dict(self):
        self.assertEqual(
            types.QuickFixAction.PrependStep("filter", {"x": "y"}).to_dict(),
            {
                "type": "prependStep",
                "moduleSlug": "filter",
                "partialParams": {"x": "y"},
            },
        )

    def test_quick_fix_from_thrift(self):
        self.assertEqual(
            types.QuickFix.from_thrift(
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
            types.QuickFix(
                types.I18nMessage("click"),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ).to_thrift(),
            ttypes.QuickFix(
                ttypes.I18nMessage("click", {}, None),
                ttypes.QuickFixAction(
                    prepend_step=ttypes.PrependStepQuickFixAction(
                        "filter", ttypes.RawParams('{"x":"y"}')
                    )
                ),
            ),
        )

    def test_quick_fix_from_dict(self):
        self.assertEqual(
            types.QuickFix.from_dict(
                {
                    "buttonText": {"id": "click", "arguments": {}},
                    "action": {
                        "type": "prependStep",
                        "moduleSlug": "filter",
                        "partialParams": {"x": "y"},
                    },
                }
            ),
            types.QuickFix(
                types.I18nMessage("click"),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ),
        )

    def test_quick_fix_to_dict(self):
        self.assertEqual(
            types.QuickFix(
                types.I18nMessage("click"),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ).to_dict(),
            {
                "buttonText": {"id": "click", "arguments": {}},
                "action": {
                    "type": "prependStep",
                    "moduleSlug": "filter",
                    "partialParams": {"x": "y"},
                },
            },
        )

    def test_render_error_from_thrift(self):
        self.assertEqual(
            types.RenderError.from_thrift(
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
            types.RenderError(
                types.I18nMessage("foo", {}),
                [
                    types.QuickFix(
                        types.I18nMessage("click"),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ).to_thrift(),
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

    def test_render_error_from_dict(self):
        self.assertEqual(
            types.RenderError.from_dict(
                {
                    "message": {"id": "err", "arguments": {}},
                    "quickFixes": [
                        {
                            "buttonText": {
                                "id": "click",
                                "arguments": {},
                                "source": "cjwmodule",
                            },
                            "action": {
                                "type": "prependStep",
                                "moduleSlug": "filter",
                                "partialParams": {"x": "y"},
                            },
                        }
                    ],
                }
            ),
            types.RenderError(
                types.I18nMessage("err", {}),
                [
                    types.QuickFix(
                        types.I18nMessage("click", {}, "cjwmodule"),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ),
        )

    def test_render_error_to_dict(self):
        self.assertEqual(
            types.RenderError(
                types.I18nMessage("err", {}),
                [
                    types.QuickFix(
                        types.I18nMessage("click", {}, "cjwmodule"),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ).to_dict(),
            {
                "message": {"id": "err", "arguments": {}},
                "quickFixes": [
                    {
                        "buttonText": {
                            "id": "click",
                            "arguments": {},
                            "source": "cjwmodule",
                        },
                        "action": {
                            "type": "prependStep",
                            "moduleSlug": "filter",
                            "partialParams": {"x": "y"},
                        },
                    }
                ],
            },
        )

    def test_render_result_from_thrift(self):
        pass  # TODO test RenderResult conversion

    def test_render_result_to_thrift(self):
        pass  # TODO test RenderResult conversion

    def test_fetch_result_from_thrift_disallow_directories(self):
        with self.assertRaisesRegex(ValueError, "must not contain directories"):
            types.FetchResult.from_thrift(
                ttypes.FetchResult("/etc/passwd", []), Path(__file__).parent
            )

    def test_fetch_result_from_thrift_disallow_hidden_files(self):
        with self.assertRaisesRegex(ValueError, "must not be hidden"):
            types.FetchResult.from_thrift(
                ttypes.FetchResult(".secrets", []), Path(__file__).parent
            )

    def test_fetch_result_from_thrift_disallow_non_files(self):
        with self.assertRaisesRegex(ValueError, "must exist"):
            types.FetchResult.from_thrift(
                ttypes.FetchResult("missing", []), self.basedir
            )

    def test_fetch_result_from_thrift_disallow_non_file(self):
        with tempfile.TemporaryDirectory(dir=str(self.basedir)) as tmpsubdir:
            with self.assertRaisesRegex(ValueError, "be a regular file"):
                types.FetchResult.from_thrift(
                    ttypes.FetchResult(Path(tmpsubdir).name, []), self.basedir
                )

    def test_fetch_result_from_thrift_happy_path(self):
        with tempfile.NamedTemporaryFile(dir=str(self.basedir)) as tf:
            self.assertEqual(
                types.FetchResult.from_thrift(
                    ttypes.FetchResult(
                        Path(tf.name).name,
                        [types.RenderError(types.I18nMessage("hi")).to_thrift()],
                    ),
                    self.basedir,
                ),
                types.FetchResult(
                    Path(tf.name), [types.RenderError(types.I18nMessage("hi"))]
                ),
            )


class NumberFormatterTest(unittest.TestCase):
    def test_format_too_many_arguments(self):
        with self.assertRaisesRegex(ValueError, "Can only format one number"):
            types.NumberFormatter("{:d}{:f}")

    def test_format_disallow_non_format(self):
        with self.assertRaisesRegex(ValueError, 'Format must look like "{:...}"'):
            types.NumberFormatter("%d")

    def test_format_disallow_field_number(self):
        with self.assertRaisesRegex(
            ValueError, "Field names or numbers are not allowed"
        ):
            types.NumberFormatter("{0:f}")

    def test_format_disallow_field_name(self):
        with self.assertRaisesRegex(
            ValueError, "Field names or numbers are not allowed"
        ):
            types.NumberFormatter("{value:f}")

    def test_format_disallow_field_converter(self):
        with self.assertRaisesRegex(ValueError, "Field converters are not allowed"):
            types.NumberFormatter("{!r:f}")

    def test_format_disallow_invalid_type(self):
        with self.assertRaisesRegex(ValueError, "Unknown format code 'T'"):
            types.NumberFormatter("{:T}")
