class UnneededExecution(Exception):
    """A render would produce useless results."""
    pass


class TabCycleError(Exception):
    """The chosen tab exists, and it depends on the output of this tab."""
    pass


class TabOutputUnreachableError(Exception):
    """The chosen tab exists, and it is empty or has an error."""
    pass
