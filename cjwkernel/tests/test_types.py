import unittest
from cjwkernel import types
from cjwkernel.thrift import ttypes


class ThriftConvertersTest(unittest.TestCase):
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

    def test_i18n_message_from_thrift(self):
        self.assertEqual(
            types.I18nMessage.from_thrift(
                ttypes.I18nMessage(
                    "modules.x.y",
                    [
                        ttypes.I18nArgument(string_value="s"),
                        ttypes.I18nArgument(i32_value=12345678),
                        ttypes.I18nArgument(double_value=0.123),
                    ],
                )
            ),
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123]),
        )

    def test_i18n_message_to_thrift(self):
        self.assertEqual(
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123]).to_thrift(),
            ttypes.I18nMessage(
                "modules.x.y",
                [
                    ttypes.I18nArgument(string_value="s"),
                    ttypes.I18nArgument(i32_value=12345678),
                    ttypes.I18nArgument(double_value=0.123),
                ],
            ),
        )

    def test_i18n_message_from_dict(self):
        self.assertEqual(
            types.I18nMessage.from_dict(
                {"id": "modules.x.y", "arguments": ["s", 12345678, 0.123]}
            ),
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123]),
        )

    def test_i18n_message_to_dict(self):
        self.assertEqual(
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123]).to_dict(),
            {"id": "modules.x.y", "arguments": ["s", 12345678, 0.123]},
        )

    def test_prepend_step_quick_fix_action_from_thrift(self):
        self.assertEqual(
            types.QuickFixAction.from_thrift(
                ttypes.QuickFixAction(
                    prepend_step=ttypes.PrependStepQuickFixAction(
                        "filter", ttypes.Params('{"x":"y"}')
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
                    "filter", ttypes.Params('{"x":"y"}')
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
                    ttypes.I18nMessage("click", []),
                    ttypes.QuickFixAction(
                        prepend_step=ttypes.PrependStepQuickFixAction(
                            "filter", ttypes.Params('{"x":"y"}')
                        )
                    ),
                )
            ),
            types.QuickFix(
                types.I18nMessage("click", []),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ),
        )

    def test_quick_fix_to_thrift(self):
        self.assertEqual(
            types.QuickFix(
                types.I18nMessage("click", []),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ).to_thrift(),
            ttypes.QuickFix(
                ttypes.I18nMessage("click", []),
                ttypes.QuickFixAction(
                    prepend_step=ttypes.PrependStepQuickFixAction(
                        "filter", ttypes.Params('{"x":"y"}')
                    )
                ),
            ),
        )

    def test_quick_fix_from_dict(self):
        self.assertEqual(
            types.QuickFix.from_dict(
                {
                    "buttonText": {"id": "click", "arguments": []},
                    "action": {
                        "type": "prependStep",
                        "moduleSlug": "filter",
                        "partialParams": {"x": "y"},
                    },
                }
            ),
            types.QuickFix(
                types.I18nMessage("click", []),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ),
        )

    def test_quick_fix_to_dict(self):
        self.assertEqual(
            types.QuickFix(
                types.I18nMessage("click", []),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ).to_dict(),
            {
                "buttonText": {"id": "click", "arguments": []},
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
                    ttypes.I18nMessage("foo", []),
                    [
                        ttypes.QuickFix(
                            ttypes.I18nMessage("click", []),
                            ttypes.QuickFixAction(
                                prepend_step=ttypes.PrependStepQuickFixAction(
                                    "filter", ttypes.Params('{"x":"y"}')
                                )
                            ),
                        )
                    ],
                )
            ),
            types.RenderError(
                types.I18nMessage("foo", []),
                [
                    types.QuickFix(
                        types.I18nMessage("click", []),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ),
        )

    def test_render_error_to_thrift(self):
        self.assertEqual(
            types.RenderError(
                types.I18nMessage("foo", []),
                [
                    types.QuickFix(
                        types.I18nMessage("click", []),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ).to_thrift(),
            ttypes.RenderError(
                ttypes.I18nMessage("foo", []),
                [
                    ttypes.QuickFix(
                        ttypes.I18nMessage("click", []),
                        ttypes.QuickFixAction(
                            prepend_step=ttypes.PrependStepQuickFixAction(
                                "filter", ttypes.Params('{"x":"y"}')
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
                    "message": {"id": "err", "arguments": []},
                    "quickFixes": [
                        {
                            "buttonText": {"id": "click", "arguments": []},
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
                types.I18nMessage("err", []),
                [
                    types.QuickFix(
                        types.I18nMessage("click", []),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ),
        )

    def test_render_error_to_dict(self):
        self.assertEqual(
            types.RenderError(
                types.I18nMessage("err", []),
                [
                    types.QuickFix(
                        types.I18nMessage("click", []),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ).to_dict(),
            {
                "message": {"id": "err", "arguments": []},
                "quickFixes": [
                    {
                        "buttonText": {"id": "click", "arguments": []},
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
