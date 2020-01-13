import unittest
from cjwkernel.types import I18nMessage, QuickFix, QuickFixAction, RenderError
from renderer.execute.types import PromptingError


class PromptingErrorTest(unittest.TestCase):
    def test_quick_fixes(self):
        err = PromptingError(
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(
                    ["B", "C"], "datetime", frozenset({"number"})
                ),
            ]
        )
        result = err.as_render_errors()
        self.assertEqual(
            result,
            [
                RenderError(
                    I18nMessage.TODO_i18n(
                        "The column “A” must be converted from Text to Numbers."
                    ),
                    [
                        QuickFix(
                            I18nMessage.TODO_i18n("Convert Text to Numbers"),
                            QuickFixAction.PrependStep(
                                "converttexttonumber", {"colnames": ["A"]}
                            ),
                        )
                    ],
                ),
                RenderError(
                    I18nMessage.TODO_i18n(
                        "The columns “B” and “C” must be converted from Dates & Times to Numbers."
                    ),
                    [
                        QuickFix(
                            I18nMessage.TODO_i18n("Convert Dates & Times to Numbers"),
                            QuickFixAction.PrependStep(
                                "converttexttonumber", {"colnames": ["B", "C"]}
                            ),
                        )
                    ],
                ),
            ],
        )

    def test_quick_fixes_convert_to_text(self):
        err = PromptingError(
            [PromptingError.WrongColumnType(["A", "B"], None, frozenset({"text"}))]
        )
        result = err.as_render_errors()
        self.assertEqual(
            result,
            [
                RenderError(
                    I18nMessage.TODO_i18n(
                        "The columns “A” and “B” must be converted to Text."
                    ),
                    [
                        QuickFix(
                            I18nMessage.TODO_i18n("Convert to Text"),
                            QuickFixAction.PrependStep(
                                "converttotext", {"colnames": ["A", "B"]}
                            ),
                        )
                    ],
                )
            ],
        )
