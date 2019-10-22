import contextlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, ContextManager, Dict


def json_encode(value: Dict[str, Any]) -> str:
    """
    Encode as JSON, without Python's stupid defaults.
    """
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def create_tempfile(prefix=None, suffix=None, dir=None) -> Path:
    # Workbench tempfiles are usually _big_ -- sometimes >1GB. In Kubernetes
    # and Docker, /tmp is mounted on tmpfs; /var/tmp isn't, so its files are on
    # disk.
    #
    # Default to /var/tmp so tempfiles don't consume RAM.
    if dir is None:
        dir = "/var/tmp"
    fd, filename = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=dir)
    os.close(fd)
    return Path(filename)


@contextlib.contextmanager
def tempfile_context(prefix=None, suffix=None, dir=None) -> ContextManager[Path]:
    path = create_tempfile(prefix=prefix, suffix=suffix, dir=dir)
    try:
        yield path
    finally:
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


def create_tempdir(prefix=None, suffix=None, dir=None) -> Path:
    # Workbench tempfiles are usually _big_ -- sometimes >1GB. In Kubernetes
    # and Docker, /tmp is mounted on tmpfs; /var/tmp isn't, so its files are on
    # disk.
    #
    # Default to /var/tmp so tempfiles don't consume RAM.
    if dir is None:
        dir = "/var/tmp"
    return Path(tempfile.mkdtemp(prefix=prefix, suffix=suffix, dir=dir))


@contextlib.contextmanager
def tempdir_context(prefix=None, suffix=None, dir=None) -> ContextManager[Path]:
    path = create_tempdir(prefix=prefix, suffix=suffix, dir=dir)
    try:
        yield path
    finally:
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(path)
