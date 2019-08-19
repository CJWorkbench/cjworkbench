from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, List, Optional
from cjworkbench.types import QuickFix


TypeNames = {"text": "Text", "number": "Numbers", "datetime": "Dates & Times"}


class UnneededExecution(Exception):
    """A render would produce useless results."""

    pass


class TabCycleError(Exception):
    """The chosen tab exists, and it depends on the output of this tab."""

    pass


class TabOutputUnreachableError(Exception):
    """The chosen tab exists, and it is empty or has an error."""

    pass


class PromptingError(Exception):
    """
    Workbench found an error in the module parameters+dataframe; ask the user.

    This type of error will lead to user-visible error messages with Quick
    Fixes. Workbench won't invoke render(): it doesn't need to because it knows
    render() isn't ready for this input.

    Example: "calculate module expects numbers but you selected text columns.
    [convert to numbers]."
    """

    @dataclass(frozen=True)
    class WrongColumnType:
        """The chosen columns exist, but they have the wrong types."""

        # Even if there are multiple wanted_types, let's only show the user
        # a single QuickFix. It's less noisy that way. (Revisit later if
        # this becomes an issue.)

        column_names: List[str]

        found_type: Optional[str]
        """
        (Wrong) type of columns.

        Iff `wanted_types` contains "text", `found_type is None`. That's
        because we allow converting from _multiple_ column types to "text" all
        at the same time. (Converting to text is a special case: it has no
        options, because all options are in the input columns' formats.)
        """

        wanted_types: FrozenSet[str]
        """
        Required types of columns.
        """

        def __post_init__(self):
            assert (self.found_type is None) == ("text" in self.wanted_types)

        @property
        def best_wanted_type_id(self):
            if "text" in self.wanted_types:
                return "text"
            elif "number" in self.wanted_types:
                return "number"
            elif "datetime" in self.wanted_types:
                return "datetime"
            else:
                raise RuntimeError(f"Unhandled wanted_types: {self.wanted_types}")

        @property
        def found_type_name(self):
            assert not self.should_be_text
            return TypeNames[self.found_type]

        @property
        def should_be_text(self):
            return self.found_type is None

        @property
        def best_wanted_type_name(self):
            return TypeNames[self.best_wanted_type_id]

        def as_error_str(self):
            """Build a message to prompt the user to use a quick fix."""
            # TODO make each quick fix get its own paragraph. (For now, quick
            # fixes are nothing but buttons.)

            names = [f"“{c}”" for c in self.column_names]
            if len(names) > 3:
                # "x", "y", "z", "a" => "x", "y", "2 others" (always more than
                # 1 other -- if there were 1 other, we might as well have
                # written the name itself)
                names[2:] = [f"{len(names) - 2} others"]
            if len(names) == 1:
                columns_str = f"The column {names[0]}"
            else:
                # English-style:
                # 2: "A" and "B"
                # 3: "A", "B" and "C"
                # 4+: "A", "B" and 2 others
                names_str = ", ".join(names[:-1]) + " and " + names[-1]
                columns_str = f"The columns {names_str}"

            if self.should_be_text:
                # Convert to Text
                return f"{columns_str} must be converted to Text."
            else:
                return (
                    f"{columns_str} must be converted "
                    f"from {self.found_type_name} to {self.best_wanted_type_name}."
                )

        def as_quick_fix(self):
            """Build a QuickFix that would resolve this error."""
            if self.should_be_text:
                prompt = f"Convert to {self.best_wanted_type_name}"
            else:
                prompt = (
                    f"Convert {self.found_type_name} to {self.best_wanted_type_name}"
                )
            params = {"colnames": self.column_names}

            if "text" in self.wanted_types:
                module_id = "converttotext"
            elif "number" in self.wanted_types:
                module_id = "converttexttonumber"
            elif "datetime" in self.wanted_types:
                module_id = "convert-date"
            else:
                raise RuntimeError(f"Unhandled wanted_types: {self.wanted_types}")

            return QuickFix(prompt, "prependModule", [module_id, params])

    def __init__(self, errors: List[PromptDontRender.WrongColumnType]):
        super().__init__("user must change something before we render")
        self.errors = errors

    def __eq__(self, other):
        return isinstance(other, self.type) and other.errors == self.errors

    def as_error_str(self) -> str:
        return "\n\n".join(err.as_error_str() for err in self.errors)

    def as_quick_fixes(self) -> List[QuickFix]:
        """Build a List of QuickFix: one per error."""
        return [err.as_quick_fix() for err in self.errors]
