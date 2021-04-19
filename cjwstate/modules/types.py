from __future__ import annotations

import json
import logging
import marshal
import re
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, NewType, Pattern, Tuple

import yaml
from cjwmodule.spec.loader import load_spec
from cjwmodule.spec.types import ModuleSpec

from cjwkernel.types import CompiledModule


logger = logging.getLogger(__name__)


ModuleId = NewType("ModuleId", str)
ModuleVersion = NewType("ModuleVersion", str)
ModuleIdAndVersion = Tuple[ModuleId, ModuleVersion]


@dataclass(frozen=True)
class ModuleZipfile:
    """Self-contained file holding a module.

    A ModuleZipfile can be transmitted between processes that share a
    filesystem, simply by passing `path`.

    Do not modify or delete the underlying zipfile while any process refers to
    it.
    """

    path: Path
    """Path to zipfile on the filesystem."""

    _VALID_PATH_PATTERN: ClassVar[Pattern] = re.compile(
        "^(?P<id>[A-Za-z][-a-zA-Z0-9]*)\.(?P<version>(?:dir-)?[a-f0-9]+|develop)\.zip$"
    )

    def __post_init__(self):
        assert self._VALID_PATH_PATTERN.match(self.path.name), (
            "`path` must look like `moduleid.abc123.zip` (got %r)" % self.path.name
        )

    @property
    def module_id(self) -> ModuleId:
        name = self.path.name
        return ModuleId(name[: name.index(".")])

    @property
    def version(self) -> ModuleVersion:
        return ModuleVersion(
            self._VALID_PATH_PATTERN.match(self.path.name).group("version")
        )

    @property
    def module_id_and_version(self) -> ModuleIdAndVersion:
        return (self.module_id, self.version)

    def _read_bytes(self, path: str) -> bytes:
        """Return bytes at `path` in zipfile.

        Raise `KeyError` if `path` does not exist.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        with zipfile.ZipFile(self.path) as zf:  # raise FileNotFoundError, BadZipFile
            info1 = zf.infolist()[0]
            if info1.is_dir():
                # GitHub-style zipfile entries are all in a subdirectory.
                # Prepend the subdirectory name.
                path = info1.filename + path
            return zf.read(path)  # raise KeyError, BadZipFile

    def _read_text(self, path: str) -> str:
        """Return bytes at `path` in zipfile as text.

        Raise `KeyError` if `path` does not exist.

        Raise `UnicodeDecodeError` if the file is invalid UTF-8.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        data = self._read_bytes(path)  # raise FileNotFoundError, BadZipFile, KeyError
        return data.decode("utf-8")  # raise UnicodeDecodeError

    def get_spec_dict(self) -> Dict[str, Any]:
        """Return parsed-but-unvalidated JSON or YAML module spec data.

        Raise `KeyError` if the module spec could not be found.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        try:
            # raise KeyError (which we'll catch), BadZipFile, ValueError (UnicodeError)
            yaml_text = self._read_text(self.module_id + ".yaml")
            try:
                return yaml.safe_load(yaml_text)
            except yaml.YAMLError as err:
                raise ValueError(
                    "YAML syntax error in %s: %s" % (self.path.name, str(err))
                ) from err
        except KeyError as original_err:
            # there is no .yaml file. Try to read a ".json" file.
            try:
                # raise KeyError (which we'll catch), BadZipFile, ValueError (UnicodeError)
                json_text = self._read_text(self.module_id + ".json")
            except KeyError:
                # there is no ".json" file, either. Tell the developer to create
                # a ".yaml" file.
                raise original_err
            return json.loads(json_text)  # raise ValueError

    @lru_cache(1)
    def get_spec(self) -> ModuleSpec:
        """Load the ModuleSpec from the zipfile.

        The spec will be validated to test that it is internally consistent.

        Raise `KeyError` if the module spec could not be found.

        Raise `ValueError` if the module spec is invalid.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        spec_dict = (
            self.get_spec_dict()
        )  # raise BadZipFile, ValueError, FileNotFoundError
        ret = load_spec(spec_dict)
        if spec_dict["id_name"] != self.module_id:
            raise ValueError("id_name must be %r" % self.module_id)
        return ret

    @lru_cache(1)
    def compile_code_without_executing(self) -> CompiledModule:
        """Return module code as a Python codeobject.

        Raise `KeyError` if the module code could not be found.

        Raise `UnicodeDecodeError` if the module code is invalid UTF-8.

        Raise `SyntaxError` if the module code is obviously invalid.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.

        [adamhooper, 2020-01-15] for now, this is what we'll pass to cjwkernel.
        When we address https://github.com/CJWorkbench/cjworkbench/issues/126
        we'll want to pass the entire zipfile through the cjwkernel interface.
        That'll be tricky because cjwkernel won't always let us use tempfiles,
        and the zipimport module isn't designed to work off-filesystem.
        """
        # raise KeyError, UnicodeDecodeError, FileNotFoundError, BadZipFile
        filename = self.module_id + ".py"
        code = self._read_text(filename)
        # raise SyntaxError
        code_object = compile(
            code,
            filename=filename,
            mode="exec",
            dont_inherit=True,
            optimize=0,  # keep assertions -- we use them!
        )
        return CompiledModule(self.module_id, marshal.dumps(code_object))

    @lru_cache(1)
    def get_optional_html(self) -> Optional[str]:
        """Return module HTML for Workbench's <iframe>, if provided.

        Return `None` if there is no `[module_id].html` file in the zipfile.

        Raise `UnicodeDecodeError` if the [module_id].html file is invalid UTF-8.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        try:
            return self._read_text(self.module_id + ".html")
        except KeyError:
            return None

    @lru_cache(1)
    def get_optional_js_module(self) -> Optional[str]:
        """Return JavaScript to pass alongside module, if any.

        Return `None` if is there is no `[module_id].js` file in the zipfile.

        Raise `UnicodeDecodeError` if the [module_id].js file is invalid UTF-8.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        try:
            return self._read_text(self.module_id + ".js")
        except KeyError:
            return None

    def read_messages_po_for_locale(self, locale_id: str) -> bytes:
        """Return the contents of the po file for the given locale.

        Raise `KeyError` is no such file exists.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid zipfile.
        """
        return self._read_bytes(f"locale/{locale_id}/messages.po")
