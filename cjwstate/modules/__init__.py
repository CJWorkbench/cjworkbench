import cjwkernel.chroot
import cjwkernel.kernel
import cjwstate.modules.staticregistry

kernel = None


def init_module_system():
    """
    Initialize the module system.

    This must be called during startup. It will:

        * Set `cjwstate.modules.kernel`, a handle on a subprocess spawner
        * Initialize the static module registry,
          `cjwstate.modules.staticregistry`.
    """
    global kernel
    # Ignore spurious init() calls. They happen in unit-testing: each unit test
    # that relies on the module system needs to ensure it's initialized.
    if kernel is None:
        kernel = cjwkernel.kernel.Kernel()
        cjwstate.modules.staticregistry._setup(kernel)
