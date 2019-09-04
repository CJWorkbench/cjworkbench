class ModuleBug(Exception):
    """The module has a bug."""


class ModuleCompileError(ModuleBug):
    """The module does not compile."""


class ModuleTimeoutError(ModuleBug):
    """The module took too long to execute."""


class ModuleExitedError(ModuleBug):
    """
    The module exited at the wrong time.

    The module's child (sandboxed process) is _meant_ to write a single message
    to its fd and then exit with code 0. This error means it exited, but it
    either did not output a single message of the correct type or did not exit
    with status code 0.
    """

    def __init__(self, exit_code: int, log: str):
        super().__init__("Module exited with code %d and logged: %s" % (exit_code, log))
        self.exit_code = exit_code
        self.log = log
