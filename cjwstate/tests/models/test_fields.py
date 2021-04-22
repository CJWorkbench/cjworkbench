import unittest
from cjwkernel import types
from cjwstate.models import fields


class DictConvertersTest(unittest.TestCase):
    def test_i18n_message_from_dict_source_library(self):
        self.assertEqual(
            fields._dict_to_i18n_message(
                {
                    "id": "modules.x.y",
                    "arguments": {"foo": "bar"},
                    "source": "cjwmodule",
                }
            ),
            types.I18nMessage("modules.x.y", {"foo": "bar"}, "cjwmodule"),
        )

    def test_i18n_message_from_dict_found_type_datetime_becomes_timestamp(self):
        # Compatibility for https://www.pivotaltracker.com/story/show/174865394
        # DELETEME when there are no CachedRenderResults from before 2020-10-01
        self.assertEqual(
            fields._dict_to_i18n_message(
                {
                    "id": "py.renderer.execute.types.PromptingError.WrongColumnType.as_quick_fixes.general",
                    "arguments": {
                        "found_type": "datetime",
                        "best_wanted_type": "number",
                    },
                }
            ),
            types.I18nMessage(
                "py.renderer.execute.types.PromptingError.WrongColumnType.as_quick_fixes.general",
                {"found_type": "timestamp", "best_wanted_type": "number"},
                None,
            ),
        )

    def test_i18n_message_from_dict_best_wanted_type_datetime_becomes_timestamp(self):
        # Compatibility for https://www.pivotaltracker.com/story/show/174865394
        # DELETEME when there are no CachedRenderResults from before 2020-10-01
        self.assertEqual(
            fields._dict_to_i18n_message(
                {
                    "id": "py.renderer.execute.types.PromptingError.WrongColumnType.as_quick_fixes.general",
                    "arguments": {
                        "found_type": "text",
                        "best_wanted_type": "datetime",
                    },
                }
            ),
            types.I18nMessage(
                "py.renderer.execute.types.PromptingError.WrongColumnType.as_quick_fixes.general",
                {"found_type": "text", "best_wanted_type": "timestamp"},
                None,
            ),
        )

    def test_i18n_message_to_dict_source_library(self):
        self.assertEqual(
            fields._i18n_message_to_dict(
                types.I18nMessage("modules.x.y", {}, "cjwmodule")
            ),
            {"id": "modules.x.y", "arguments": {}, "source": "cjwmodule"},
        )

    def test_i18n_message_from_dict_source_module(self):
        self.assertEqual(
            fields._dict_to_i18n_message(
                {"id": "modules.x.y", "arguments": {"foo": "bar"}, "source": "module"}
            ),
            types.I18nMessage("modules.x.y", {"foo": "bar"}, "module"),
        )

    def test_i18n_message_to_dict_source_module(self):
        self.assertEqual(
            fields._i18n_message_to_dict(
                types.I18nMessage("modules.x.y", {}, "module")
            ),
            {"id": "modules.x.y", "arguments": {}, "source": "module"},
        )

    def test_i18n_message_from_dict_no_source(self):
        self.assertEqual(
            fields._dict_to_i18n_message(
                {"id": "modules.x.y", "arguments": ["s", 12345678, 0.123]}
            ),
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123], None),
        )

    def test_i18n_message_to_dict_no_source(self):
        self.assertEqual(
            fields._i18n_message_to_dict(
                types.I18nMessage("modules.x.y", ["s", 12345678, 0.123], None)
            ),
            {"id": "modules.x.y", "arguments": ["s", 12345678, 0.123]},
        )

    def test_prepend_step_quick_fix_action_from_dict(self):
        self.assertEqual(
            fields._dict_to_quick_fix_action(
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
            fields._quick_fix_action_to_dict(
                types.QuickFixAction.PrependStep("filter", {"x": "y"})
            ),
            {
                "type": "prependStep",
                "moduleSlug": "filter",
                "partialParams": {"x": "y"},
            },
        )

    def test_quick_fix_from_dict(self):
        self.assertEqual(
            fields._dict_to_quick_fix(
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
                types.I18nMessage("click", {}, None),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ),
        )

    def test_quick_fix_to_dict(self):
        self.assertEqual(
            fields._quick_fix_to_dict(
                types.QuickFix(
                    types.I18nMessage("click", {}, None),
                    types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                )
            ),
            {
                "buttonText": {"id": "click", "arguments": {}},
                "action": {
                    "type": "prependStep",
                    "moduleSlug": "filter",
                    "partialParams": {"x": "y"},
                },
            },
        )

    def test_render_error_from_dict(self):
        self.assertEqual(
            fields._dict_to_render_error(
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
                types.I18nMessage("err", {}, None),
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
            fields._render_error_to_dict(
                types.RenderError(
                    types.I18nMessage("err", {}, None),
                    [
                        types.QuickFix(
                            types.I18nMessage("click", {}, "cjwmodule"),
                            types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                        )
                    ],
                )
            ),
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

    def test_column_from_dict(self):
        self.assertEqual(
            fields._dict_to_column({"name": "A", "type": "number", "format": "{:d}"}),
            types.Column("A", types.ColumnType.Number("{:d}")),
        )

    def test_fetch_error_from_dict(self):
        self.assertEqual(
            fields._dict_to_fetch_error({"message": {"id": "err", "arguments": {}}}),
            types.FetchError(types.I18nMessage("err", {}, None)),
        )

    def test_fetch_error_from_dict_pre_2021_04_22(self):
        # We used to store "quick_fixes" in FetchError -- really, it was the
        # exact same thing as RenderError.
        #
        # These old structures remain in the database, so we need to support
        # them.
        #
        # Why not allow quick_fixes? Because we don't know that FetchError and
        # RenderError will always be identical, moving forward. Let's not
        # publish a whole big feature for module authors just to save ourselves
        # ten lines of code: in the future, it might cost us dearly.
        self.assertEqual(
            fields._dict_to_fetch_error(
                {"message": {"id": "err", "arguments": {}}, "quick_fixes": []}
            ),
            types.FetchError(types.I18nMessage("err", {}, None)),
        )

    def test_fetch_error_to_dict(self):
        self.assertEqual(
            fields._fetch_error_to_dict(
                types.FetchError(types.I18nMessage("err", {}, None))
            ),
            {"message": {"id": "err", "arguments": {}}},
        )
