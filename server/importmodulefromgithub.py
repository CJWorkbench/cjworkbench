from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
import logging
import os
from pathlib import Path
import shutil
import tempfile
from typing import List, Optional, Set
import git
from git.exc import GitCommandError
import yaml
from server import minio
from server.models import ModuleVersion
from server.models.module_version import validate_module_spec


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    pass


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
        raise ValidationError(f'Multiple ".{extensions}" files detected. '
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
                                             'package-lock.json'])
        IgnoreHtmlPatterns = IgnorePatterns([])
        IgnoreJavascriptPatterns = IgnorePatterns(['*.config.js'])

        # these throw ValidationError
        code = _find_file(dirpath, {'py'}, IgnoreCodePatterns)
        spec = _find_file(dirpath, {'json', 'yaml', 'yml'}, IgnoreSpecPatterns)
        html = _find_file(dirpath, {'html'}, IgnoreHtmlPatterns)
        javascript = _find_file(dirpath, {'js'}, IgnoreJavascriptPatterns)

        if not spec:
            raise ValidationError('Missing ".json" or ".yaml" module-spec '
                                  'file. Please write one.')

        if not code:
            raise ValidationError('Missing ".py" module-code file. '
                                  'Please write one.')

        return cls(spec, code, html, javascript)


# Now check if the module is importable and defines the render function
def validate_python_functions(code_path: Path):
    # execute the module, as a test
    try:
        spec = importlib.util.spec_from_file_location('test', str(code_path))
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
    except Exception:  # TODO what exception?
        raise ValidationError('Cannot load module')

    if hasattr(test_module, 'render'):
        if callable(test_module.render):
            return
        else:
            raise ValidationError("Module render() function isn't callable.")
    elif hasattr(test_module, 'fetch'):
        if callable(test_module.fetch):
            return
        else:
            raise ValidationError("Module fetch() function isn't callable.")
    else:
        raise ValidationError("Module render() function is missing.")


# Load a module after cloning from github
# This is the guts of our module import, also a good place to hook into for
# tests (bypassing github access). Returns a dictionary of info to display to
# user (category, repo name, author, id_name)
def import_module_from_directory(version: str, importdir: Path, force_reload=False):
    # check that right files exist
    module_files = ModuleFiles.load_from_dirpath(importdir)

    # load spec
    module_spec_text = module_files.spec.read_text(encoding='utf-8')
    if module_files.spec.suffix == '.json':
        try:
            module_spec = json.loads(module_spec_text)
        except ValueError as err:
            raise ValidationError('JSON syntax error in %s: %s' %
                                  (module_files.spec.name, str(err)))
    else:
        try:
            module_spec = yaml.safe_load(module_spec_text)
        except yaml.YAMLError as err:
            raise ValidationError('YAML syntax error in %s: %s' %
                                  (module_files.spec.name, str(err)))
    validate_module_spec(module_spec)  # raises ValidationError
    validate_python_functions(module_files.code)

    id_name = module_spec['id_name']

    if not force_reload:
        # Don't allow importing the same version twice
        try:
            ModuleVersion.objects.get(id_name=id_name,
                                      source_version_hash=version)
            raise ValidationError(
                f'Version {version} of module {id_name}'
                ' has already been imported'
            )
        except ModuleVersion.DoesNotExist:
            # this is what we want
            pass

    if module_files.javascript:
        js_module = module_files.javascript.read_text(encoding='utf-8')
    else:
        js_module = ''

    # Copy code to S3
    prefix = '%s/%s/' % (id_name, version)

    try:
        # If files already exist, delete them so we can overwrite them.
        #
        # This can race: a worker may be loading the code to execute it. But
        # races are unlikely to affect anybody because:
        #
        # * If force_reload=True we're in dev or test, where we control
        #   everything.
        # * Otherwise, we've already checked there's no ModuleVersion, so
        #   probably nothing is trying and load what we're deleting here.
        minio.remove_recursive(minio.ExternalModulesBucket, prefix)
    except FileNotFoundError:
        pass  # common case: we aren't overwriting code

    minio.fput_directory_contents(minio.ExternalModulesBucket, prefix,
                                  Path(importdir))

    # If that succeeds, initialise module in our database
    module_version = ModuleVersion.create_or_replace_from_spec(
        module_spec,
        source_version_hash=version,
        js_module=js_module
    )

    logger.info('Imported module %s' % id_name)

    return module_version


# Top level import, clones from github
# If force_relaod, reloads the module even if the version hasn't changed
# (normally, this is an error). On success, returnd a dict with (category,
# repo name, author, id_name) to tell user what happened
def import_module_from_github(url, force_reload=False):
    with tempfile.TemporaryDirectory(prefix='importmodulefromgithub') as td:
        # Clone into a _subdirectory_ of `td`. That way if the subdir is
        # deleted (as `git clone` is wont to do),
        # `tempfile.TemporaryDirectory()`'s `finally` block will still be able
        # to delete `td`.
        importdir = os.path.join(td, 'repo')
        os.mkdir(importdir)

        clone_kwargs = {}
        if url.startswith('https://github.com/'):
            # depth=1: do not clone entire repo -- just the latest commit. Not
            # every HTTP server supports `depth`. (Indeed, our integration-test
            # HTTP server doesn't.) But we know GitHub does.
            clone_kwargs['depth'] = 1

        try:
            repo = git.Repo.clone_from(url, importdir, **clone_kwargs)
        except GitCommandError as err:
            raise ValidationError(
                f'Unable to clone {url}: {str(err)}'
            )

        version = repo.head.commit.hexsha[:7]

        # Nix ".git" subdir: not a Git repo any more, just a dir
        shutil.rmtree(os.path.join(importdir, '.git'))

        return import_module_from_directory(version, Path(importdir), force_reload)
