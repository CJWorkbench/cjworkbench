from dataclasses import dataclass, field
import errno
import os
from pathlib import Path
from typing import FrozenSet, Optional
import pyroute2
from . import c


seccomp_bpf_bytes = Path(__file__).with_name("sandbox-seccomp.bpf").read_bytes()


@dataclass(frozen=True)
class NetworkConfig:
    """
    Network configuration that lets children access the Internet.

    The kernel will create a veth interface and associated iptables rules to
    route traffic from the child to the Internet via network address
    translation (NAT). The iptables rules will prevent access to private IP
    addresses.

    We do not yet support IPv6, because Kubernetes support is shaky. Follow
    https://github.com/kubernetes/kubernetes/issues/62822.

    Here's how networking works. Each child process gets its own network
    namespace. The kernel creates a veth pair, and it passes the "child" veth
    interface to the child process. The kernel configures NAT from that device
    using iptables -- denying traffic to private network addresses (such as our
    Postgres database's address). The child process brings up its network
    interface and can only see the public Internet.

    After the child dies, the iptables rules are leaked. (This is fine, as of
    [2019-11-11], for the reason described in the next paragraph.)

    Beware if running multiple children at once that all access the Internet.
    Each must have a unique interface name and IP addresses. [2019-11-11] We
    only do networking with EDITABLE_CHROOT, which we use as a singleton.
    Therefore, we can use the same interface names and IP addresses with each
    invocation.

    The default values match those in `cjwkernel/setup-sandboxes.sh`. Don't
    edit one without editing the other.
    """

    kernel_veth_name: str = "cjw-veth-kernel"
    """
    Name of veth interface run by the kernel.

    Maximum length is 15 characters. Any longer gives NetlinkError 34.

    This name must not conflict with any other network device in the kernel's
    container.
    """

    child_veth_name: str = "cjw-veth-child"
    """
    Name of veth interface run by the child.

    Maximum length is 15 characters. Any longer gives NetlinkError 34.

    This name must not conflict with any other network device in the kernel's
    container. (The kernel creates this device before sending it into the
    child's network namespace.)
    """

    kernel_ipv4_address: str = "192.168.123.1"
    """
    IPv4 address of the kernel.

    This must not conflict with any other IP address in the kernel's container.

    This should be a private address. Be sure it doesn't conflict with your
    network's addresses. Kubernetes uses 10.0.0.0/8; Docker uses 172.16.0.0/12.
    The hard-coded "192.168.123/24" should be safe for Docker and Kubernetes.

    The child will use this address as its default gateway.
    """

    child_ipv4_address: str = "192.168.123.2"
    """
    IPv4 address of the child.

    The kernel will maintain iptables rules to route from this IP address to
    the public Internet.

    This must be in the same `/24` network block as `kernel_ipv4_address`.
    """


@dataclass(frozen=True)
class SandboxConfig:
    chroot_dir: Optional[Path] = None
    """
    Setting for "chroot" security layer.

    If `chroot_dir` is set, it must point to a directory on the filesystem.
    """

    network: Optional[NetworkConfig] = None
    """
    If set, network configuration so child processes can access the Internet.

    If None, child processes have no network interfaces.
    """

    skip_sandbox_except: FrozenSet[str] = field(default_factory=frozenset)
    """
    Security layers to enable in child processes. (DO NOT USE IN PRODUCTION.)

    By default, child processes are sandboxed: user code should not be able to
    access the rest of the system. (In particular, it should not be able to
    access parent-process state; influence parent-process behavior in any way
    but its stdout, stderr and exit code; or communicate with any internal
    services.)
    
    Our layers of sandbox security overlap: for instance: we (a) restrict the
    user code to run as non-root _and_ (b) disallow root from escaping its
    chroot. We can't test layer (b) unless we disable layer (a); and that's
    what this feature is for.

    By default, all sandbox features are enabled. To enable only a subset, set
    `skip_sandbox_except` to a `frozenset()` with one or more of the following
    strings:

    * "drop_capabilities": limit root's capabilities
    """


def sandbox_child_from_pycloner(child_pid: int, config: SandboxConfig) -> None:
    """
    Sandbox the child process from the pycloner side of things.

    The child must wait for this to complete before it embarks upon its own
    sandboxing adventure.
    """
    _write_namespace_uidgid(child_pid)
    if config.network is not None:
        _setup_network_namespace_from_pycloner(config.network, child_pid)


def sandbox_child_self(config: SandboxConfig) -> None:
    """
    Sandbox our own process.

    This must not be called before pycloner finishes calling
    sandbox_child_from_pycloner().
    """
    _Sandbox(config).run()


@dataclass(frozen=True)
class _Sandbox:
    config: SandboxConfig

    def _should_sandbox(self, feature: str) -> bool:
        """
        Return `True` if we should call a particular sandbox function.

        This should _always_ return `True` on production code. The function only
        exists to help with unit testing.
        """
        if self.config.skip_sandbox_except:
            # test code only
            return feature in self.config.skip_sandbox_except
        else:
            # production code
            return True

    def run(self) -> None:
        """
        prevent child code from interacting with the rest of our system.

        tasks with rationale ('[x]' means, "unit-tested"):

        [x] bring up external network
        [x] wait for pycloner to write uid_map
        [x] close `sock` (so "pycloner" does not misbehave)
        [x] drop capabilities (like cap_sys_admin)
        [x] set seccomp filter
        [x] setuid to 1000
        [x] use chroot (so children can't see other files)
        """
        if self.config.network is not None:
            _install_network(self.config.network)
        if self._should_sandbox("no_new_privs"):
            _set_no_new_privs()
        if self.config.chroot_dir is not None:
            _chroot(self.config.chroot_dir)
        if self._should_sandbox("setuid"):
            _setuid()
        if self._should_sandbox("drop_capabilities"):
            _drop_capabilities()
        if self._should_sandbox("seccomp"):
            _install_seccomp(seccomp_bpf_bytes)


def _write_namespace_uidgid(child_pid: int) -> None:
    """
    Write /proc/child_pid/uid_map and /proc/child_pid/gid_map.

    Why call this? Because otherwise, the called code can do it for us. That
    would mean root in the child would be equal to root in the parent -- so the
    child could, for instance, modify files owned outside of it.

    ref: man user_namespaces(7).
    """
    Path(f"/proc/{child_pid}/uid_map").write_text("0 100000 65536")
    Path(f"/proc/{child_pid}/setgroups").write_text("deny")
    Path(f"/proc/{child_pid}/gid_map").write_text("0 100000 65536")


def _setup_network_namespace_from_pycloner(
    config: NetworkConfig, child_pid: int
) -> None:
    """
    Send new veth device to `child_pid`'s network namespace.

    See `_network()` for the child's logic. Read the `NetworkConfig`
    docstring to understand how the network namespace works.
    """
    with pyroute2.IPRoute() as ipr:
        # Avoid a race: what if another forked process already created this
        # interface?
        #
        # If that's the case, assume the other process has already exited
        # (because [2019-11-11] we only run one networking-enabled child at a
        # time). So the veth device is about to be deleted anyway.
        try:
            ipr.link("del", ifname=config.kernel_veth_name)
        except pyroute2.NetlinkError as err:
            if err.code == errno.ENODEV:
                pass  # common case -- the device doesn't exist
            else:
                raise

        # Create kernel_veth + child_veth veth pair
        ipr.link(
            "add",
            ifname=config.kernel_veth_name,
            peer=config.child_veth_name,
            kind="veth",
        )

        # Bring up kernel_veth
        kernel_veth_index = ipr.link_lookup(ifname=config.kernel_veth_name)[0]
        ipr.addr(
            "add",
            index=kernel_veth_index,
            address=config.kernel_ipv4_address,
            prefixlen=24,
        )
        ipr.link("set", index=kernel_veth_index, state="up")

        # Send child_veth to child namespace
        child_veth_index = ipr.link_lookup(ifname=config.child_veth_name)[0]
        ipr.link("set", index=child_veth_index, net_ns_pid=child_pid)


def _chroot(root: Path) -> None:
    """
    Enter a restricted filesystem, so absolute paths are relative to `root`.

    Why call this? So the user can't read files from our filesystem (which
    include our secrets and our users' secrets); and the user can't *write*
    files to our filesystem (which might inject code into a parent process).

    SECURITY: entering a chroot is not enough. To prevent this process from
    accessing files outside the chroot, this process must drop its ability to
    chroot back _out_ of the chroot. Use _drop_capabilities().

    SECURITY: TODO: switch from chroot to pivot_root. pivot_root makes it far
    harder for root to break out of the jail. It needs a process-specific mount
    namespace. But on Kubernetes (and Docker), we'd need so many privileges to
    pivot_root that we'd be _decreasing_ security. Find out how to do it with
    fewer privileges.

    For now, since we don't use a separate mount namespace, chroot doesn't
    add much "security" in the case of privilege escalation: root will be able
    to escape the chroot. (Even root doesn't have permission to read our
    secrets, though.) Chroot isn't to allay evildoers: it's so child-code
    developers see the filesystem tree we want them to see.
    """
    os.chroot(str(root))
    os.chdir("/")


def _install_network(config: NetworkConfig) -> None:
    """
    Set up networking, assuming pycloner passed us a network interface.

    Set ip address of veth interface, then bring it up.

    Also bring up the "lo" interface.

    This requires CAP_NET_ADMIN. Use the "drop_capabilities" sandboxing step
    afterwards to prevent further fiddling.
    """
    with pyroute2.IPRoute() as ipr:
        lo_index = ipr.link_lookup(ifname="lo")[0]
        ipr.link("set", index=lo_index, state="up")

        veth_index = ipr.link_lookup(ifname=config.child_veth_name)[0]
        ipr.addr(
            "add", index=veth_index, address=config.child_ipv4_address, prefixlen=24
        )
        ipr.link("set", index=veth_index, state="up")
        ipr.route("add", gateway=config.kernel_ipv4_address)


def _drop_capabilities():
    """
    Drop all capabilities in the caller.

    Also, set the process "securebits" to prevent regaining capabilities.

    Why call this? So if user code manages to setuid to root (which should be
    impossible), it still won't have permission to call dangerous kernel code.
    (For example: after dropping privileges, "pivot_root" will fail with
    EPERM, even for root.)

    ref: http://people.redhat.com/sgrubb/libcap-ng/
    ref: man capabilities(7)
    """
    # straight from man capabilities(7):
    # "An  application  can  use  the following call to lock itself, and all of
    # its descendants, into an environment where the only way of gaining
    # capabilities is by executing a program with associated file capabilities"
    c.libc_prctl_set_securebits()
    # And now, _drop_ the capabilities (and we can never gain them again)
    # Drop the Bounding set...
    c.libc_prctl_capbset_drop_all_capabilities()
    # ... and drop permitted/effective/inheritable capabilities
    c.libcap_cap_set_proc_empty_capabilities()


def _set_no_new_privs():
    """
    Prevent a setuid bit on a file from restoring capabilities.
    """
    c.libc_prctl_pr_set_no_new_privs(1)


def _install_seccomp(bpf_bytes):
    """
    Install a whitelist filter to prevent unwanted syscalls.

    Why call this? Two reasons:

    1. Redundancy: if there's a Linux bug, there's a good chance our seccomp
       filter may prevent an attacker from exploiting it.
    2. Speculative execution: seccomp implicitly prevents _all_ syscalls from
       exploiting Spectre-type CPU security bypasses.

    Docker comes with seccomp by default, making seccomp mostly redundant. But
    Kubernetes 1.14 still doesn't use seccomp, and [2019-11-07] that's what we
    use on prod.

    To maintain our whitelist, read `docker/seccomp/README.md`. The compiled
    file, for x86-64, belongs in `cjwkernel/pycloner/sandbox-seccomp.bpf`.

    Requires `no_new_privs` sandbox (or CAP_SYS_ADMIN).
    """
    c.libc_prctl_pr_set_seccomp_mode_filter(bpf_bytes)


def _setuid():
    """
    Drop root: switch to UID 1000.

    Why call this? Because Linux gives special capabilities to root (even after
    we drop privileges).

    ref: man setresuid(2)
    """
    os.setresuid(1000, 1000, 1000)
    os.setresgid(1000, 1000, 1000)
