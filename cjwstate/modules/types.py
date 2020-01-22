from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
import marshal
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, NewType, Pattern, Tuple
import re
import zipfile
import yaml
from cjwkernel.types import CompiledModule
from cjwstate.modules.param_dtype import ParamDType
from .module_loader import validate_module_spec
from .param_spec import ParamSpec


ModuleId = NewType("ModuleId", str)
ModuleVersion = NewType("ModuleVersion", str)
ModuleIdAndVersion = Tuple[ModuleId, ModuleVersion]


@dataclass(frozen=True)
class ModuleSpec:
    """
    Dict-like object representing a valid module spec.

    See `module_spec_schema.yaml` for the spec definition, or look to
    `staticmodules/` for example JSON and YAML files.

    You may pass this to `ModuleVersion.create_or_replace_from_spec()`.
    """

    id_name: str
    name: str
    category: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)

    deprecated: Optional[Dict[str, str]] = None
    icon: str = ""
    link: str = ""
    description: str = ""
    loads_data: bool = False
    uses_data: Optional[bool] = None
    html_output: bool = False  # janky -- really we should check ModuleZipfile
    has_zen_mode: bool = False
    row_action_menu_entry_title: str = ""
    help_url: str = ""
    param_schema: Optional[Dict[str, Any]] = None
    parameters_version: Optional[int] = None

    def get_uses_data(self):
        if self.uses_data is None:
            return self.uses_data
        else:
            return not self.loads_data

    @property
    def default_params(self) -> Dict[str, Any]:
        return self.get_param_schema().coerce(None)

    @property
    def param_fields(self) -> List[ParamSpec]:
        return [ParamSpec.from_dict(d) for d in self.parameters]

    # Returns a dict of DTypes for all parameters
    def get_param_schema(self) -> ParamDType.Dict:
        if self.param_schema is not None:
            # Module author wrote a schema in the YAML, to define storage of 'custom' parameters
            json_schema = self.param_schema
            return ParamDType.parse({"type": "dict", "properties": json_schema})
        else:
            # Usual case: infer schema from module parameter types
            # Use of dict here means schema is not sensitive to parameter ordering, which is good
            return ParamDType.Dict(
                dict(
                    (f.id_name, f.dtype)
                    for f in self.param_fields
                    if f.dtype is not None
                )
            )


@dataclass(frozen=True)
class ModuleZipfile:
    """
    Self-contained file holding a module.

    A ModuleZipfile can be transmitted between processes that share a
    filesystem, simply by passing `path`.
    
    Do not modify or delete the underlying zipfile while any process refers to
    it.
    """

    path: Path
    """
    Path to zipfile on the filesystem.
    """

    _VALID_PATH_PATTERN: ClassVar[Pattern] = re.compile(
        "^(?P<id>[A-Za-z][-a-zA-Z0-9]*)\.(?P<version>(?:dir-)?[a-f0-9]+|internal|develop)\.zip$"
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
        """
        Return bytes at `path` in zipfile.

        Raise `KeyError` if `path` does not exist.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        with zipfile.ZipFile(self.path) as zf:  # raise FileNotFoundError, BadZipFile
            return zf.read(path)  # raise KeyError, BadZipFile

    def _read_text(self, path: str) -> str:
        """
        Return bytes at `path` in zipfile as text.

        Raise `KeyError` if `path` does not exist.

        Raise `UnicodeDecodeError` if the file is invalid UTF-8.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        data = self._read_bytes(path)  # raise FileNotFoundError, BadZipFile, KeyError
        return data.decode("utf-8")  # raise UnicodeDecodeError

    @lru_cache(1)
    def get_spec(self) -> ModuleSpec:
        """
        Load the ModuleSpec from the zipfile.

        The spec will be validated to test that it is internally consistent.

        Raise `KeyError` if the module spec could not be found.

        Raise `ValueError` if the module spec is invalid.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        try:
            # raise KeyError (which we'll catch), BadZipFile, ValueError (UnicodeError)
            yaml_text = self._read_text(self.module_id + ".yaml")
            try:
                spec_dict = yaml.safe_load(yaml_text)
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
            spec_dict = json.loads(json_text)  # raise ValueError

        validate_module_spec(spec_dict)  # raise ValueError
        if spec_dict["id_name"] != self.module_id:
            raise ValueError("id_name must be %r" % self.module_id)
        return ModuleSpec(**spec_dict)

    @lru_cache(1)
    def compile_code_without_executing(self) -> CompiledModule:
        """
        Return module code as a Python codeobject.

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
        """
        Return module HTML for Workbench's <iframe>, if provided.

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
        """
        Return JavaScript to pass alongside module, if any.

        Return `None` if is there is no `[module_id].js` file in the zipfile.

        Raise `UnicodeDecodeError` if the [module_id].js file is invalid UTF-8.

        Raise `FileNotFoundError` or `BadZipFile` if `self.path` is not a valid
        zipfile.
        """
        try:
            return self._read_text(self.module_id + ".js")
        except KeyError:
            return None

    def get_param_schema_version(self) -> str:
        """
        Version of param_schema. Changes whenever spec.get_param_schema() changes.

        This is used in caching: if params were cached under
        param_schema_version=v1 and now the module has param_schema_version=v2,
        then we must call the module's migrate_params() on the params.
        """
        if self.version == "internal":
            # We version internal modules' param specs explicitly.
            return "v%d" % self.get_spec().parameters_version
        else:
            # "develop" is handled specially in cjwstate/params.py. For GitHub
            # sha1, a new version forces migrate_params().
            return self.version
