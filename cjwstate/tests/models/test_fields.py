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
            types.I18nMessage("modules.x.y", ["s", 12345678, 0.123]),
        )

    def test_i18n_message_to_dict_no_source(self):
        self.assertEqual(
            fields._i18n_message_to_dict(
                types.I18nMessage("modules.x.y", ["s", 12345678, 0.123])
            ),
            {"id": "modules.x.y", "arguments": ["s", 12345678, 0.123]},
        )

    def test_i18n_message_from_dict_invalid_source(self):
        with self.assertRaises(ValueError):
            fields._dict_to_i18n_message(
                {"id": "modules.x.y", "arguments": {}, "source": "random"}
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
                types.I18nMessage("click"),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ),
        )

    def test_quick_fix_to_dict(self):
        self.assertEqual(
            fields._quick_fix_to_dict(
                types.QuickFix(
                    types.I18nMessage("click"),
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
            fields._render_error_to_dict(
                types.RenderError(
                    types.I18nMessage("err", {}),
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
