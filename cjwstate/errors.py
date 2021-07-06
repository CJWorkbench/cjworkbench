from __future__ import annotations

from typing import Dict, FrozenSet, List, Literal, NamedTuple, Tuple, Union

from cjwkernel.i18n import trans
from cjwkernel.types import Column, QuickFix, QuickFixAction, RenderError

ColumnType = Literal["text", "number", "date", "timestamp"]


_QUICK_FIX_CONVERSIONS: Dict[Tuple[ColumnType, ColumnType], str] = {
    ("text", "date"): "converttexttodate",
    ("text", "timestamp"): "convert-date",
    ("text", "number"): "converttexttonumber",
    ("timestamp", "date"): "converttimestamptodate",
}
"""Hard-coded list of quick-fix converters, referencing suggested-modules.txt.

Each module must accept a "colnames" parameter.

There are no conversions to text: those are a special case.
"""


class PromptingError(Exception):
    """Workbench found an error in the module parameters+dataframe; ask the user.

    This type of error will lead to user-visible error messages with Quick
    Fixes. Workbench won't invoke render(): it doesn't need to because it knows
    render() isn't ready for this input.

    Example: "calculate module expects numbers but you selected text columns.
    [convert to numbers]."
    """

    class CannotCoerceValueToNumber(NamedTuple):
        """The user supplied text that cannot be coerced to the Number."""

        value: str

        def as_render_error(self) -> RenderError:
            """Build a RenderError that describes this error."""
            return RenderError(
                trans(
                    "py.renderer.execute.types.PromptingError.CannotCoerceValueToNumber",
                    default="“{value}” is not a number. Please enter a number.",
                    arguments={"value": self.value},
                )
            )

    class CannotCoerceValueToTimestamp(NamedTuple):
        """The user supplied text that cannot be coerced to Timestamp."""

        value: str

        def as_render_error(self) -> RenderError:
            """Build a RenderError that describes this error."""
            return RenderError(
                trans(
                    "py.renderer.execute.types.PromptingError.CannotCoerceValueToTimestamp",
                    default="“{value}” is not a timestamp. Please enter a value with the format “YYYY-MM-DD” or “YYYY-MM-DDThh:mmZ”.",
                    arguments={"value": self.value},
                )
            )

    class WrongColumnType(NamedTuple):
        """The chosen columns exist, but they have the wrong types."""

        # Even if there are multiple wanted_types, let's only show the user
        # a single QuickFix. It's less noisy that way. (Revisit later if
        # this becomes an issue.)

        column_names: List[str]

        found_type: Literal[None, "number", "date", "timestamp"]
        """(Wrong) type of columns.

        Iff `wanted_types` contains "text", `found_type is None`. That's
        because we allow converting from _multiple_ column types to "text" all
        at the same time. (Converting to text is a special case: it has no
        options, because all options are in the input columns' formats.)
        """

        wanted_types: FrozenSet[ColumnType]
        """Required types of columns."""

        @property
        def best_wanted_type(self):
            if "text" in self.wanted_types:
                return "text"
            elif "number" in self.wanted_types:
                return "number"
            elif "date" in self.wanted_types:
                return "date"
            elif "timestamp" in self.wanted_types:
                return "timestamp"
            else:
                raise RuntimeError(f"Unhandled wanted_types: {self.wanted_types}")

        @property
        def should_be_text(self):
            return self.found_type is None

        def as_render_error(self) -> RenderError:
            """Build RenderError(s) that describe this error.

            Render errors should include at least one QuickFix to resolve the error.

            Errors the user can see:

                (wanted_types = {date, timestamp})
                "A", "B" and 2 others are Text.
                     [Convert to Date]
                     [Convert to Timestamp]

                (wanted_types = {number})
                "A" and "B" are Date. Select Number.

                (wanted_types = {text} - special case because all types convert to text)
                "A" is not Text.
                     [Convert to Text]
            """
            if self.should_be_text:
                icu_args = {
                    "columns": len(self.column_names),
                    **{str(i): name for i, name in enumerate(self.column_names)},
                }
                # i18n: The parameter {columns} will contain the total number of columns that need to be converted; you will also receive the column names as {0}, {1}, {2}, etc.
                message = trans(
                    "py.renderer.execute.types.PromptingError.WrongColumnType.as_error_message.shouldBeText",
                    default="{ columns, plural, offset:2"
                    " =1 {“{0}” is not Text.}"
                    " =2 {“{0}” and “{1}” are not Text.}"
                    " =3 {“{0}”, “{1}” and “{2}” are not Text.}"
                    " other {“{0}”, “{1}” and # others are not Text.}}",
                    arguments=icu_args,
                )
                return RenderError(
                    message,
                    quick_fixes=[
                        QuickFix(
                            trans(
                                "py.renderer.execute.types.PromptingError.WrongColumnType.as_quick_fixes.shouldBeText",
                                default="Convert to Text",
                            ),
                            QuickFixAction.PrependStep(
                                "converttotext", dict(colnames=self.column_names)
                            ),
                        )
                    ],
                )
            else:
                icu_args = {
                    "columns": len(self.column_names),
                    "found_type": self.found_type,
                    **{str(i): name for i, name in enumerate(self.column_names)},
                }

                quick_fixes = [
                    QuickFix(
                        # i18n: The parameter {wanted_type} will have values among "text", "number", "date", "timestamp" or "other". ("other" may translate to "".)
                        trans(
                            "py.renderer.execute.types.PromptingError.WrongColumnType.general.quick_fix",
                            default="Convert to {wanted_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}",
                            arguments=dict(wanted_type=wanted_type),
                        ),
                        QuickFixAction.PrependStep(
                            _QUICK_FIX_CONVERSIONS[(self.found_type, wanted_type)],
                            dict(colnames=self.column_names),
                        ),
                    )
                    for wanted_type in sorted(self.wanted_types)  # sort for determinism
                    if (self.found_type, wanted_type) in _QUICK_FIX_CONVERSIONS
                ]

                if quick_fixes:
                    # i18n: The parameter {columns} will contain the total number of columns that need to be converted; you will also receive the column names: {0}, {1}, {2}, etc. The parameter {found_type} will be "date", "text", "number", "timestamp" or "other". ("other" may translate to "".)
                    message = trans(
                        "py.renderer.execute.types.PromptingError.WrongColumnType.general.message.before_convert_buttons",
                        default="{columns, plural, offset:2"
                        " =1 {“{0}” is {found_type, select, text {Text} number {Number} timestamp {Timestamp} date {Date} other {}}.}"
                        " =2 {“{0}” and “{1}” are {found_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}.}"
                        " =3 {“{0}”, “{1}” and “{2}” are {found_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}.}"
                        " other {“{0}”, “{1}” and # others are {found_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}.}}",
                        arguments=icu_args,
                    )
                else:
                    # i18n: The parameter {columns} will contain the total number of columns that need to be converted; you will also receive the column names: {0}, {1}, {2}, etc. The parameters {found_type} and {best_wanted_type} will be "date", "text", "number", "timestamp" or "other". ("other" may translate to "".)
                    message = trans(
                        "py.renderer.execute.types.PromptingError.WrongColumnType.general.message.without_convert_buttons",
                        default="{columns, plural, offset:2"
                        " =1 {“{0}” is {found_type, select, text {Text} number {Number} timestamp {Timestamp} date {Date} other {}}. Select {best_wanted_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}.}"
                        " =2 {“{0}” and “{1}” are {found_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}. Select {best_wanted_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}.}"
                        " =3 {“{0}”, “{1}” and “{2}” are {found_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}. Select {best_wanted_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}.}"
                        " other {“{0}”, “{1}” and # others are {found_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}. Select {best_wanted_type, select, text {Text} number {Number} date {Date} timestamp {Timestamp} other {}}.}}",
                        arguments=dict(
                            best_wanted_type=self.best_wanted_type, **icu_args
                        ),
                    )

                return RenderError(message, quick_fixes=quick_fixes)

    def __init__(self, errors: List[PromptingError.WrongColumnType]):
        super().__init__("user must change something before we render")
        self.errors = errors

    def as_render_errors(self) -> List[RenderError]:
        return [error.as_render_error() for error in self.errors]


PromptingErrorSubtype = Union[
    PromptingError.WrongColumnType,
    PromptingError.CannotCoerceValueToNumber,
    PromptingError.CannotCoerceValueToTimestamp,
]


class PromptingErrorAggregator:
    def __init__(self):
        self.groups = {}  # found_type => { wanted_types => column_names }
        self.ungrouped_errors = []
        # Errors are first-come-first-reported, per type. We get that because
        # Python 3.7+ dicts iterate in insertion order.

    def extend(self, errors: List[PromptingErrorSubtype]) -> None:
        for error in errors:
            self.add(error)

    def add(self, error: PromptingErrorSubtype) -> None:
        if isinstance(error, PromptingError.WrongColumnType):
            if "text" in error.wanted_types:
                found_type = None
            else:
                found_type = error.found_type
            group = self.groups.setdefault(found_type, {})
            names = group.setdefault(error.wanted_types, [])
            for name in error.column_names:
                if name not in names:
                    names.append(name)
        else:
            self.ungrouped_errors.append(error)

    def raise_if_nonempty(self):
        if not self.groups and not self.ungrouped_errors:
            return

        errors = []
        for found_type, group in self.groups.items():
            for wanted_types, column_names in group.items():
                errors.append(
                    PromptingError.WrongColumnType(
                        column_names, found_type, wanted_types
                    )
                )
        errors.extend(self.ungrouped_errors)
        raise PromptingError(errors)
