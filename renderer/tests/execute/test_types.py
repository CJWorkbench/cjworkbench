import unittest
from cjworkbench.types import QuickFix
from renderer.execute.types import PromptingError


class PromptingErrorTest(unittest.TestCase):
    def test_as_quick_fixes(self):
        err = PromptingError([
            PromptingError.WrongColumnType(['A'], 'text',
                                           frozenset({'number'})),
            PromptingError.WrongColumnType(['B', 'C'], 'datetime',
                                           frozenset({'number'})),
        ])
        result = err.as_quick_fixes()
        self.assertEqual(result, [
            QuickFix('Convert "A" to Numbers', 'prependModule',
                     ['converttexttonumber', {'colnames': ['A']}]),
            QuickFix('Convert "B", "C" to Numbers', 'prependModule',
                     ['converttexttonumber', {'colnames': ['B', 'C']}]),
        ])
