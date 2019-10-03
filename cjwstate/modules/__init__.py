import cjwkernel.forkserver
import cjwkernel.kernel
import cjwstate.modules.staticregistry

__all__ = ["kernel"]


kernel = None


def init_module_system():
    """
    Initialize the module system.

    This must be called during startup. It will:

        * Set the calling process to be a subreaper (PR_SET_CHILD_SUBREAPER)
        * Set `cjwstate.modules.kernel`, a handle on a subprocess spawner
        * Initialize the static module registry,
          `cjwstate.modules.staticregistry`.
    """
    global kernel
    # Ignore spurious init() calls. They happen in unit-testing: each unit test
    # that relies on the module system needs to ensure it's initialized.
    if kernel is None:
        cjwkernel.forkserver.install_calling_process_as_subreaper()
        kernel = cjwkernel.kernel.Kernel()
        cjwstate.modules.staticregistry._setup(kernel)
