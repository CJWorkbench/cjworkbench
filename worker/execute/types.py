from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, List
from cjworkbench.types import QuickFix


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
        column_names: List[str]
        found_type: str
        wanted_types: FrozenSet[str]

        def as_quick_fix(self):
            """Build a QuickFix that would resolve this error."""
            # Even if there are multiple wanted_types, let's only show the user
            # a single QuickFix. It's less noisy that way. (Revisit later if
            # this becomes an issue.)
            #
            # ... ignore self.found_type for now because [2019-04-10] none of
            # our converters are split by input type.

            # 'names': user-visible colnames
            names = ', '.join([f'"{c}"' for c in self.column_names])
            # 'colnames': param value for the module
            colnames = ','.join(self.column_names)
            params = {'colnames': colnames}

            if 'text' in self.wanted_types:
                return QuickFix(f'Convert {names} to Text',
                                'prependModule', ['converttotext', params])
            elif 'number' in self.wanted_types:
                return QuickFix(f'Convert {names} to Numbers',
                                'prependModule', ['extract-numbers', params])
            elif 'datetime' in self.wanted_types:
                return QuickFix(f'Convert {names} to Dates & Times',
                                'prependModule', ['convert-date', params])
            else:
                raise RuntimeError(
                    f'Unhandled wanted_types: {self.wanted_types}'
                )


    def __init__(self, errors: List[PromptDontRender.WrongColumnType]):
        super().__init__('user must change something before we render')
        self.errors = errors

    def __eq__(self, other):
        return isinstance(other, self.type) and other.errors == self.errors

    def as_quick_fixes(self) -> List[QuickFix]:
        """Build a List of QuickFix: one per error."""
        return [err.as_quick_fix() for err in self.errors]
