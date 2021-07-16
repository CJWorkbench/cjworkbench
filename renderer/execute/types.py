from pathlib import Path
from typing import List, NamedTuple

from cjwkernel.types import Column


class Tab(NamedTuple):
    """Tab description."""

    slug: str
    """Tab identifier, unique in its Workflow."""

    name: str
    """Tab name, provided by the user."""


class StepResult(NamedTuple):
    """All the renderer needs to know to render subsequent Steps.

    A StepResult with no columns has status "error" or "unreachable". Subsequent
    steps won't render.
    """

    path: Path
    """Trusted Arrow file containing the output."""

    columns: List[Column]
    """Shape of the Arrow file."""


class TabResult(NamedTuple):
    """All the renderer needs to render dependent tabs and publish datasets.

    A TabResult with no columns has status "error" or "unreachable". Subsequent
    steps won't render.
    """

    tab_name: str
    """Tab name."""

    path: Path
    """Trusted Arrow file containing the output."""

    columns: List[Column]
    """Shape of the Arrow file."""


class UnneededExecution(Exception):
    """A render would produce useless results."""


class TabCycleError(Exception):
    """The chosen tab exists, and it depends on the output of this tab."""


class TabOutputUnreachableError(Exception):
    """The chosen tab exists, and it is empty or has an error."""


class NoLoadedDataError(Exception):
    """This first Step in its Tab has a spec with loads_data: false.

    Modules with `loads_data: false` may assume the input table is non-empty.
    Their `render()` might crash if we called them with input `None`. Better
    to raise this error.
    """
