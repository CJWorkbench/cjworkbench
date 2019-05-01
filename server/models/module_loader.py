"""
Loads module specs and code from the filesystem.

Steps to loading a module:

    1. Find all the files. (deliverable: ModuleFiles instance)
    2. Load its spec. (deliverable: ModuleSpec instance)
    3. Load its Python code. (deliverable: types.Module with valid functions)
"""


from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import jsonschema
import sys
import threading
from typing import List, Optional, Set
import yaml


with (
    Path(__file__).parent / 'module_spec_schema.yaml'
).open('rt') as spec_file:
    _validator = jsonschema.Draft7Validator(
        yaml.safe_load(spec_file),
        format_checker=jsonschema.FormatChecker()
    )


def validate_module_spec(spec):
    """
    Validate that the spec is valid.

    Raise ValueError otherwise.

    "Valid" means:

    * `spec` adheres to `server/models/module_spec_schema.yaml`
    * `spec.parameters[*].id_name` are unique
    * `spec.parameters[*].visible_if[*].id_name` are valid
    * If `spec.parameters[*].options` and `default` exist, `default` is valid
    * `spec.parameters[*].visible_if[*].value` is/are valid if it's a menu
    * `spec.parameters[*].tab_parameter` point to valid params
    """
    # No need to do i18n on these errors: they're only for admins. Good thing,
    # too -- most of the error messages come from jsonschema, and there are
    # _plenty_ of potential messages there.
    messages = []

    for err in _validator.iter_errors(spec):
        messages.append(err.message)
    if messages:
        # Don't bother validating the rest. The rest of this method assumes
        # the schema is valid.
        raise ValueError('; '.join(messages))

    param_lookup = {}
    for param in spec['parameters']:
        id_name = param['id_name']

        if id_name in param_lookup:
            messages.append(f"Param '{id_name}' appears twice")
        else:
            param_lookup[id_name] = param

    # check 'default' is valid in menu/radio
    for param in spec['parameters']:
        if 'default' in param and 'options' in param:
            options = [o['value'] for o in param['options']
                       if isinstance(o, dict)]  # skip 'separator'
            if param['default'] not in options:
                messages.append(
                    f"Param '{param['id_name']}' has a 'default' that is not "
                    "in its 'options'"
                )

    # Now that check visible_if refs
    for param in spec['parameters']:
        try:
            visible_if = param['visible_if']
        except KeyError:
            continue

        try:
            ref_param = param_lookup[visible_if['id_name']]
        except KeyError:
            messages.append(
                f"Param '{param['id_name']}' has visible_if "
                f"id_name '{visible_if['id_name']}', which does not exist",
            )
            continue

        if (
            'options' in ref_param
            and not isinstance(visible_if['value'], list)
        ):
            messages.append(
                f"Param '{param['id_name']}' needs its visible_if.value "
                f"to be an Array of Strings, since '{visible_if['id_name']}' "
                "has options."
            )

        if (
            'options' in ref_param
            or 'menu_items' in ref_param
        ):
            if_values = visible_if['value']
            if isinstance(if_values, list):
                if_values = set(if_values)
            else:
                if_values = set(if_values.split('|'))

            if 'options' in ref_param:
                options = set(o['value'] for o in ref_param['options']
                              if isinstance(o, dict))  # skip 'separator'
            elif 'menu_items' in ref_param:
                options = (  # deprecated: allow indexes and labels
                    set(range(len(ref_param['menu_items'].split('|'))))
                    | set(ref_param['menu_items'].split('|'))
                )

            missing = if_values - options
            if missing:
                messages.append(
                    f"Param '{param['id_name']}' has visible_if values "
                    f"{repr(missing)} not in '{ref_param['id_name']}' options"
                )

    # Check tab_parameter refs
    for param in spec['parameters']:
        try:
            tab_parameter = param['tab_parameter']
        except KeyError:
            continue  # we aren't referencing a "tab" parameter

        if tab_parameter not in param_lookup:
            messages.append(
                f"Param '{param['id_name']}' has a 'tab_parameter' "
                "that is not in 'parameters'"
            )
        elif param_lookup[tab_parameter]['type'] != 'tab':
            messages.append(
                f"Param '{param['id_name']}' has a 'tab_parameter' "
                "that is not a 'tab'"
            )

    if messages:
        raise ValueError('; '.join(messages))


@dataclass(frozen=True)
class IgnorePatterns:
    patterns: List[str]

    def match(self, path):
        return any(path.match(pattern) for pattern in self.patterns)


def _find_file(dirpath: Path, extensions: Set[str],
               ignore_patterns: IgnorePatterns) -> Optional[Path]:
    # ext = "py" or "{json|yaml}"
    globbed = []
    for extension in extensions:
        globbed.extend(dirpath.glob('*.' + extension))

    paths = [p for p in globbed if not ignore_patterns.match(p)]
    if len(paths) > 1:
        raise ValueError(f'Multiple ".{extensions}" files detected. '
                         'Please delete the wrong one(s).')
    if len(paths) == 1:
        return paths[0]
    else:
        return None


@dataclass(frozen=True)
class ModuleFiles:
    spec: Path
    code: Path
    html: Optional[Path] = None
    javascript: Optional[Path] = None

    @classmethod
    def load_from_dirpath(cls, dirpath: Path) -> ModuleFiles:
        IgnoreCodePatterns = IgnorePatterns(['__init__.py', 'setup.py',
                                             'test_*.py'])
        IgnoreSpecPatterns = IgnorePatterns(['package.json',
                                             'package-lock.json',
                                             '.travis.yml'])
        IgnoreHtmlPatterns = IgnorePatterns([])
        IgnoreJavascriptPatterns = IgnorePatterns(['*.config.js'])

        # these throw ValueError
        code = _find_file(dirpath, {'py'}, IgnoreCodePatterns)
        spec = _find_file(dirpath, {'json', 'yaml', 'yml'}, IgnoreSpecPatterns)
        html = _find_file(dirpath, {'html'}, IgnoreHtmlPatterns)
        javascript = _find_file(dirpath, {'js'}, IgnoreJavascriptPatterns)

        if not spec:
            raise ValueError('Missing ".json" or ".yaml" module-spec '
                             'file. Please write one.')

        if not code:
            raise ValueError('Missing ".py" module-code file. '
                             'Please write one.')

        return cls(spec, code, html, javascript)


class PathLoader(importlib.abc.SourceLoader):
    def __init__(self, name: str, path: Path):
        super().__init__()
        self.name = name
        self.path = path

    # override ResourceLoader
    def get_data(self, path):
        return self.path.read_bytes()

    # override ExecutionLoader
    def get_filename(self, path):
        return f'<Module {self.name}>'


def load_python_module(name: str, code_path: Path):
    """
    Convert from `pathlib.Path` to Python module.

    Raise `ValueError` if Path isn't executable Python code.
    """
    # execute the module, as a test
    loader = PathLoader(name, code_path)
    spec = importlib.util.spec_from_loader(
        (
            # generate unique package name -- no conflicts, please!
            #
            # (We temporarily inject this into sys.modules below.)
            f'{__package__}._dynamic_{threading.get_ident()}'
            f'.{name}.{code_path.stem}'
        ),
        loader
    )

    try:
        module = importlib.util.module_from_spec(spec)
    except SyntaxError as err:
        raise ValueError('Syntax error in %s: %s' % (name, str(err)))

    try:
        # add to sys.modules, so "@dataclass()" can read the module data
        # Needed when `from __future__ import annotations` in Python 3.7.
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as err:  # really, code can raise _any_ error
        raise ValueError('%s could not execute: %s' % (name, str(err)))
    finally:
        del sys.modules[spec.name]

    return module


# Now check if the module is importable and defines the render function
def validate_python_functions(code_path: Path):
    test_module = load_python_module(code_path.stem, code_path)

    if hasattr(test_module, 'render'):
        if callable(test_module.render):
            return
        else:
            raise ValueError('%s.render is not callable' % code_path.name)
    elif hasattr(test_module, 'fetch'):
        if callable(test_module.fetch):
            return
        else:
            raise ValueError('%s.fetch is not callable' % code_path.name)
    else:
        raise ValueError('Missing %s.render (or .fetch)' % code_path.name)


class ModuleSpec:
    """
    Dict-like object representing a valid module spec.

    See `module_spec_schema.yaml` for the spec definition, or look to
    `server/modules/` for example JSON and YAML files.

    You may pass this to `ModuleVersion.create_or_replace_from_spec()`.
    """

    def __init__(self, id_name: str, name: str, category: str,
                 parameters: List[object] = [], **kwargs):
        self.data = {
            'id_name': id_name,
            'name': name,
            'category': category,
            'parameters': parameters,
            **kwargs
        }
        self.id_name = id_name
        self.name = name
        self.category = category
        self.parameters = parameters

    # duck-type dict
    def __contains__(self, key):
        return self.data.__contains__(key)

    # duck-type dict
    def __getitem__(self, key):
        return self.data.__getitem__(key)

    # duck-type dict
    def get(self, key, default=None):
        return self.data.get(key, default)

    # duck-type dict
    def keys(self):
        return self.data.keys()

    # duck-type dict
    def values(self):
        return self.data.values()

    # duck-type dict
    def items(self):
        return self.data.items()

    # duck-type dict
    def __iter__(self):
        return self.data.__iter__()

    @classmethod
    def load_from_path(self, path: Path) -> ModuleSpec:
        """
        Parse from a path.

        Raise ValueError on syntax or semantic error.
        """

        text = path.read_text(encoding='utf-8')
        if path.suffix == '.json':
            try:
                data = json.loads(text)
            except ValueError as err:
                raise ValueError('JSON syntax error in %s: %s' %
                                 (path.name, str(err)))
        else:
            try:
                data = yaml.safe_load(text)
            except yaml.YAMLError as err:
                raise ValueError('YAML syntax error in %s: %s' %
                                 (path.name, str(err)))

        validate_module_spec(data)  # raises ValueError
        return ModuleSpec(**data)
