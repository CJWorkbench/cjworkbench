import signal


class ModuleError(Exception):
    """The module has a bug."""


class ModuleTimeoutError(ModuleError):
    """The module took too long to execute."""

    def __init__(self, module_slug: str, timeout: float):
        super().__init__("Module '%s' timed out (limit %ds)" % (module_slug, timeout))


class ModuleExitedError(ModuleError):
    """The module exited at the wrong time.

    The module's child (sandboxed process) is _meant_ to write a single message
    to its fd and then exit with code 0. This error means it exited, but it
    either did not output a single message of the correct type or did not exit
    with status code 0.
    """

    def __init__(self, module_slug: str, exit_code: int, log: str):
        super().__init__(
            "Module '%s' exited with code %d and logged: %s"
            % (module_slug, exit_code, log)
        )
        self.exit_code = exit_code
        self.log = log


def format_for_user_debugging(err: ModuleError) -> str:
    """Return a string for showing hapless users.

    Users should never see ModuleError. Only developers should see ModuleError,
    in logs and emailed alerts. But we need to show users _something_, and a
    hint of an error message greatly helps us talk with our users our debugging
    effort.

    These messages aren't i18n-ized, because they are intended for Python
    developers and CPython stack traces aren't localized.
    """
    if isinstance(err, ModuleTimeoutError):
        return "timed out"
    elif isinstance(err, ModuleExitedError):
        try:
            # If the exit code is -9, for instance, return 'SIGTERM'
            exit_text = signal.Signals(-err.exit_code).name
        except ValueError:
            # Exit code 1 goes to "1"
            exit_text = "exit code %d" % err.exit_code
        # Usually, the last line of output is the one that differentiates it.
        # In particular, this is the "ValueError" line in a Python stack trace.
        for line in reversed(err.log.split("\n")):
            # Ignore newlines at the end of output.
            if line:
                last_line = line
                break
        else:
            last_line = None
        if last_line:
            # "exit code 1: ValueError: invalid JSON..."
            return "%s: %s" % (exit_text, last_line or "(empty)")
        else:
            # "SIGSEGV"
            return exit_text
    else:
        message = str(err)
        if message:
            return type(err).__name__ + ": " + message
        else:
            return type(err).__name__
