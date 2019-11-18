from __future__ import annotations
import contextlib
from dataclasses import dataclass, field
import errno
import os
import os.path
from pathlib import Path
import threading
from typing import Callable, ContextManager, Iterator, List, Tuple
from cjwkernel.util import tempdir_context, tempfile_context
from cjwkernel.errors import ModuleExitedError


def _walk_and_delete_upper_files(
    chroot: Chroot, should_delete: Callable[[Path, Path], bool] = lambda root_path: True
) -> None:
    """
    Delete files and directories from `root` that are in `upper` but not `base`.

    Ignore files and directories for which `should_delete(root_path) == False`.
    """
    # lightweight recursion: (dirpath, scandir iterator) at each
    # level of nesting
    #
    # We scandir *chroot.upper*. This is where all the _changes_ are
    # recorded; so we want it to appear empty (except for maybe a few
    # empty directories that mirror directories in chroot.base).
    #
    # DO NOT edit chroot.upper directly: that gives undefined behavior.
    # Delete from chroot.root.
    stack: List[Tuple[Path, Iterator[os.DirEntry]]] = [
        (chroot.upper, os.scandir(str(chroot.upper)))
    ]

    while stack:
        cur_dir, cur_scandir = stack[-1]
        try:
            entry: os.DirEntry = next(cur_scandir)
        except StopIteration:
            stack.pop()
            if cur_dir != chroot.upper:  # we're done
                # Delete the directory itself, unless it's in base layer or
                # we didn't delete its children.
                relative_path = Path(cur_dir).relative_to(chroot.upper)
                base_path = chroot.base / relative_path
                root_path = chroot.root / relative_path
                if not base_path.exists() and should_delete(root_path):
                    try:
                        root_path.rmdir()
                    except OSError as err:
                        if err.errno == errno.ENOTEMPTY:
                            pass
                        else:
                            raise
            continue

        relative_path = Path(entry.path).relative_to(chroot.upper)
        root_path = chroot.root / relative_path
        if entry.is_dir(follow_symlinks=False):
            if root_path.is_mount():
                # Don't follow mountpoints. /root/.local/share/virtualenvs
                # is a mountpoint in dev mode, to cache installed Python
                # modules.
                continue
            stack.append((Path(entry.path), os.scandir(entry.path)))
        elif should_delete(root_path):
            root_path.unlink()


@dataclass
class Chroot:
    root: Path
    """
    Path where we'll call `chroot`.

    This contains the file tree the child module will see.
    """

    base: Path
    """
    Path to the "base layer" of the overlayfs filesystem.

    We examine the base layer as we "clean up" changes in the upper layer.
    """

    upper: Path
    """
    Path holding the differences between `base` and `root`, as per overlayfs.

    See https://www.kernel.org/doc/Documentation/filesystems/overlayfs.txt to
    learn what the upper layer is.
    """

    lock: threading.Lock = field(default_factory=threading.Lock)
    """
    Sanity check.

    This lock should not be strictly necessary; it is used as an elaborate
    assertion that we aren't using the same chroot twice. (A bug would mean
    one module could read another module's data.)
    """

    def acquire_context(self) -> ContextManager[ChrootContext]:
        self.lock.acquire(timeout=0.01)
        try:
            return ChrootContext(self)
        finally:
            self.lock.release()


class ChrootContext:
    """
    Provide helpers for callers to communicate with modules.

    Callers can create a directory using ctx.tempdir_context() and then write
    files into it. When they pass this ChrootContext to `kernel.compile()` and
    company, kernel will invoke code that is allowed to write to these
    directories ... and thanks to the miracle of OverlayFS, those writes will
    not affect the temporary directory. The kernel will call
    `reown_output_file(path)` to move output files into the input dir.

    Division of responsibilities:

        Caller calls `with chroot.acquire_context() as ctx` and
        `with ctx.tempdir_context(...) as path:`.

        Caller passes `ctx` to kernel methods such as `kernel.render()`. The
        kernel's methods document which paths will be written.

        Kernel calls `with writable_file(input_path):` (if the API method,
        e.g., "render", is to let the module write to a file.

        Kernel calls `clear_directory_caches()`.

        Kernel runs the module, chrooted. The module reads from and writes to
        `root` -- and writes end up in `upper`.

        The `__exit__()` of `writable_file()` will overwrite the file at
        `input_path` with the module's output.

        (At this point, the caller may continue using the files the caller
        wrote to `chroot.upper`.)

        The `__exit__()` of `ChrootContext` will wipe the chroot filesystem
        back to its initial state: no data whatsoever.
    """

    def __init__(self, chroot: Chroot):
        self.chroot = chroot

    def _clear_all_edits(self) -> None:
        """
        Restore chroot to mirror `layers/base`.

        After running this, the `upper/` layer should be a "no-op" layer: no
        path (except `/root/.local/share/virtualenvs, on dev)` will modify the
        meaning of the `base` layer. (TODO ensure `upper/` is actually empty,
        for performance.)

        Beware: with overlayfs, we're not allowed to simply delete from the
        `upper` layer, because it's mounted by overlayfs. According to
        https://www.kernel.org/doc/Documentation/filesystems/overlayfs.txt :

            Changes to the underlying filesystems while part of a mounted overlay
            filesystem are not allowed.  If the underlying filesystem is changed,
            the behavior of the overlay is undefined, though it will not result in
            a crash or deadlock.

        ("offline edits" would be a nifty solution: 1. unmount; 2. delete
        edits; 3. remount. But mount+umount are only allowed in privileged
        mode, and we don't want to use privileged mode.)

        ... so instead, we "revert" changes through logic. We assume the caller
        _never_ edits a file provided in the "base" layer; and we trust that
        module code never runs with enough permission to edit files.
        """
        _walk_and_delete_upper_files(self.chroot)

    def clear_unowned_edits(self) -> None:
        """
        Delete all files not owned by caller.

        Ideally, this would use overlayfs layers: the module code would write
        to a third layer. We can't! According to
        https://www.kernel.org/doc/Documentation/filesystems/overlayfs.txt :

            Changes to the underlying filesystems while part of a mounted overlay
            filesystem are not allowed.  If the underlying filesystem is changed,
            the behavior of the overlay is undefined, though it will not result in
            a crash or deadlock.

        ("offline edits" would be a nifty solution: 1. unmount; 2. delete
        edits; 3. remount. But mount+umount are only allowed in privileged
        mode, and we don't want to use privileged mode.)

        ... so instead, we "revert" changes through logic. We assume the module
        cannot write a file owned by root: even if the module exploits a
        privilege-escalation 0day, UID-0 in the module container is different
        from UID-0 in the caller's container. Therefore, any high-UID file is
        an "unowned edit" and must be deleted.
        """
        _walk_and_delete_upper_files(
            self.chroot, lambda path: path.stat().st_uid > 65535
        )

    def _assert_empty(self, path: Path) -> None:
        garbage = list(path.glob("*"))
        if garbage:
            raise RuntimeError("%r should be empty. %s leaked!" % (path, garbage[0]))

    def __enter__(self):
        self._clear_all_edits()  # in case we're recovering after a restart (e.g., on dev)
        return self

    def __exit__(self, *exc):
        self._clear_all_edits()

    @contextlib.contextmanager
    def tempdir_context(self, prefix=None, suffix=None) -> ContextManager[Path]:
        """
        Yield a directory where files are writable to us and read-only to modules.

        The directory will be world-readable.

        Module code that _writes_ to this directory will produce new output in
        self.chroot.upper.
        """
        tmp = self.chroot.root / "var" / "tmp"
        with tempdir_context(prefix=prefix, suffix=suffix, dir=tmp) as path:
            path.chmod(0o755)
            yield path

    @contextlib.contextmanager
    def tempfile_context(
        self, prefix=None, suffix=None, dir=None
    ) -> ContextManager[Path]:
        """
        Yield a temporary file in `dir`, readable by module code.

        `dir` must have been yielded from `self.tempdir_context()`.
        """
        assert dir is not None and str(dir).startswith(
            str(self.chroot.root)
        ), "please pass a dir yielded from Chroot.tempdir_context()."
        with tempfile_context(prefix=prefix, suffix=suffix, dir=dir) as path:
            path.chmod(0o644)
            yield path

    @contextlib.contextmanager
    def writable_file(self, path: Path) -> ContextManager[None]:
        """
        Flag a file as "writable" by a module.

        `path` must exist -- that is, the module must be "overwriting" a file
        (writing to overlayfs, which stores the written file in an output
        layer).

        The logic is: save the original attributes; then make the file
        world-writable. When the context exits, restore the original
        attributes.

        Raise ModuleExitedError if the module tried to inject a symlink.
        """
        old_stat = path.stat()
        path.chmod(0o666)

        try:
            yield
        finally:
            self._reown_output_file(path, old_stat)

    def _reown_output_file(self, path: Path, old_stat: os.stat_result) -> None:
        if not path.exists():
            # module deleted path
            raise ModuleExitedError(0, "Module bug: %r was deleted" % path)
        if path.is_symlink():
            # If the module wrote a symlink, DO NOT READ IT. That's a security
            # issue -- the module could write "/etc/passwd" and then we'd read it.
            raise ModuleExitedError(0, "SECURITY: module output a symlink")
        if not path.is_file():
            raise ModuleExitedError(0, "Module bug: output must be a regular file")

        os.chmod(path, old_stat.st_mode & 0o7777)
        os.chown(path, old_stat.st_uid, old_stat.st_gid)


_chroots = Path("/var/lib/cjwkernel/chroot")
_base = Path("/var/lib/cjwkernel/chroot-layers/base")


EDITABLE_CHROOT = Chroot(
    _chroots / "editable" / "root", _base, _chroots / "editable" / "upperfs" / "upper"
)
READONLY_CHROOT = Chroot(
    _chroots / "readonly" / "root",
    # TODO remove "base/upper" logic. Readonly chroot doesn't use/need them.
    _base,
    _chroots / "readonly" / "upper",
)
READONLY_CHROOT_CONTEXT = ChrootContext(READONLY_CHROOT)  # without locking
