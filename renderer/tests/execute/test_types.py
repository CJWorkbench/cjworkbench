import unittest
from cjworkbench.types import QuickFix
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
                    "Convert Text to Numbers",
                    "prependModule",
                    ["converttexttonumber", {"colnames": ["A"]}],
                ),
                QuickFix(
                    "Convert Date & Time to Numbers",
                    "prependModule",
                    ["converttexttonumber", {"colnames": ["B", "C"]}],
                ),
            ],
        )

        error_result = err.as_error_str()
        self.assertEqual(
            error_result,
            (
                "The column “A” must be converted from Text to Numbers.\n\n"
                "The columns “B” and “C” must be converted from Date & Time to Numbers."
            ),
        )
