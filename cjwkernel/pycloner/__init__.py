"""
Entrypoint for using pycloner.

Usage:

    # pycloner.Client() is slow; ideally, you'll just call it during startup.
    with pycloner.Client(
        child_main="mymodule.main",
        environment={"LC_ALL": "C.UTF-8"},
        preload_imports=["pandas"],
    ) as cloner:
        # cloner.spawn_child() is fast; call it as many times as you like.
        child_process: pycloner.ChildProcess = cloner.spawn_child(
            args=["arg1", "arg2"],  # List of picklable Python objects
            process_name="child-1",
            sandbox_config=SandboxConfig(
                chroot_dir=Path("/path/to/chroot/dir"),
                network=NetworkConfig()
            )
        )

        # child_process has pid, stdin, stdout, stderr.
        child.stdin.close()  # or write to it, if you like
        result = read_result_from_pipes(child.stdout, child.stderr)
        # you may call child.kill() if it takes too long.
        returncode = child.wait()  # you _must_ call child.wait()!
"""
from .client import ChildProcess, Client
from .protocol import SandboxConfig, NetworkConfig

__all__ = ["Client", "ChildProcess", "NetworkConfig", "SandboxConfig"]
