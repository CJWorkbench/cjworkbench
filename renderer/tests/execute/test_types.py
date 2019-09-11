import unittest
from cjwkernel.types import I18nMessage, QuickFix, QuickFixAction
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
        quick_fixes_result = err.as_quick_fixes()
        self.assertEqual(
            quick_fixes_result,
            [
                QuickFix(
                    I18nMessage.TODO_i18n("Convert Text to Numbers"),
                    QuickFixAction.PrependStep(
                        "converttexttonumber", {"colnames": ["A"]}
                    ),
                ),
                QuickFix(
                    I18nMessage.TODO_i18n("Convert Dates & Times to Numbers"),
                    QuickFixAction.PrependStep(
                        "converttexttonumber", {"colnames": ["B", "C"]}
                    ),
                ),
            ],
        )

        error_result = err.as_error_str()
        self.assertEqual(
            error_result,
            (
                "The column “A” must be converted from Text to Numbers.\n\n"
                "The columns “B” and “C” must be converted from Dates & Times to Numbers."
            ),
        )

    def test_quick_fixes_convert_to_text(self):
        err = PromptingError(
            [PromptingError.WrongColumnType(["A", "B"], None, frozenset({"text"}))]
        )
        quick_fixes_result = err.as_quick_fixes()
        self.assertEqual(
            quick_fixes_result,
            [
                QuickFix(
                    I18nMessage.TODO_i18n("Convert to Text"),
                    QuickFixAction.PrependStep(
                        "converttotext", {"colnames": ["A", "B"]}
                    ),
                )
            ],
        )

        error_result = err.as_error_str()
        self.assertEqual(
            error_result, "The columns “A” and “B” must be converted to Text."
        )
