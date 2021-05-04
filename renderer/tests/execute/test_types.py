import unittest

from cjwkernel.types import I18nMessage, QuickFix, QuickFixAction, RenderError
from renderer.execute.types import PromptingError


class PromptingErrorTest(unittest.TestCase):
    maxDiff = None

    def test_quick_fixes(self):
        err = PromptingError(
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(
                    ["B", "C"], "text", frozenset({"number"})
                ),
            ]
        )
        result = err.as_render_errors()
        self.assertEqual(
            result,
            [
                RenderError(
                    I18nMessage(
                        "py.renderer.execute.types.PromptingError.WrongColumnType.general.message.before_convert_buttons",
                        {
                            "columns": 1,
                            "0": "A",
                            "found_type": "text",
                        },
                        None,
                    ),
                    [
                        QuickFix(
                            I18nMessage(
                                "py.renderer.execute.types.PromptingError.WrongColumnType.general.quick_fix",
                                {"wanted_type": "number"},
                                None,
                            ),
                            QuickFixAction.PrependStep(
                                "converttexttonumber", {"colnames": ["A"]}
                            ),
                        )
                    ],
                ),
                RenderError(
                    I18nMessage(
                        "py.renderer.execute.types.PromptingError.WrongColumnType.general.message.before_convert_buttons",
                        {
                            "columns": 2,
                            "0": "B",
                            "1": "C",
                            "found_type": "text",
                        },
                        None,
                    ),
                    [
                        QuickFix(
                            I18nMessage(
                                "py.renderer.execute.types.PromptingError.WrongColumnType.general.quick_fix",
                                {"wanted_type": "number"},
                                None,
                            ),
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
                    I18nMessage(
                        "py.renderer.execute.types.PromptingError.WrongColumnType.as_error_message.shouldBeText",
                        {"columns": 2, "0": "A", "1": "B"},
                        None,
                    ),
                    [
                        QuickFix(
                            I18nMessage(
                                "py.renderer.execute.types.PromptingError.WrongColumnType.as_quick_fixes.shouldBeText",
                                {},
                                None,
                            ),
                            QuickFixAction.PrependStep(
                                "converttotext", {"colnames": ["A", "B"]}
                            ),
                        )
                    ],
                )
            ],
        )

    def test_quick_fixes_multiple_conversions(self):
        # For example, "linechart" X axis may be temporal or number
        err = PromptingError(
            [
                PromptingError.WrongColumnType(
                    ["A"], "text", frozenset({"number", "date", "timestamp"})
                )
            ]
        )
        result = err.as_render_errors()
        self.assertEqual(
            result,
            [
                RenderError(
                    I18nMessage(
                        "py.renderer.execute.types.PromptingError.WrongColumnType.general.message.before_convert_buttons",
                        {
                            "columns": 1,
                            "0": "A",
                            "found_type": "text",
                        },
                        None,
                    ),
                    [
                        QuickFix(
                            I18nMessage(
                                "py.renderer.execute.types.PromptingError.WrongColumnType.general.quick_fix",
                                {"wanted_type": "date"},
                                None,
                            ),
                            QuickFixAction.PrependStep(
                                "converttexttodate", {"colnames": ["A"]}
                            ),
                        ),
                        QuickFix(
                            I18nMessage(
                                "py.renderer.execute.types.PromptingError.WrongColumnType.general.quick_fix",
                                {"wanted_type": "number"},
                                None,
                            ),
                            QuickFixAction.PrependStep(
                                "converttexttonumber", {"colnames": ["A"]}
                            ),
                        ),
                        QuickFix(
                            I18nMessage(
                                "py.renderer.execute.types.PromptingError.WrongColumnType.general.quick_fix",
                                {"wanted_type": "timestamp"},
                                None,
                            ),
                            QuickFixAction.PrependStep(
                                "convert-date", {"colnames": ["A"]}
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_quick_fixes_no_conversions_yet(self):
        # Let's see how our users get stuck and *then* decide whether to build
        # other, more esoteric converters. [2021-05-03, adamhooper] *I* would
        # love a UNIX timestamp <=> integer converter; but would other users be
        # too confused if a quick-fix suggested to add one in the wrong place?
        err = PromptingError(
            [PromptingError.WrongColumnType(["A"], "timestamp", frozenset({"number"}))]
        )
        result = err.as_render_errors()
        self.assertEqual(
            result,
            [
                RenderError(
                    I18nMessage(
                        "py.renderer.execute.types.PromptingError.WrongColumnType.general.message.without_convert_buttons",
                        {
                            "columns": 1,
                            "0": "A",
                            "found_type": "timestamp",
                            "best_wanted_type": "number",
                        },
                        None,
                    ),
                    [],
                ),
            ],
        )
