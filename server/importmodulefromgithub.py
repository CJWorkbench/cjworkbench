import importlib.util
import json
import logging
import os
import shutil
import tempfile
import git
from git.exc import GitCommandError
from server.models import ModuleVersion
from server.models.module_version import validate_module_spec


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    pass


# Check that we have one .py and one .json file in the repo root dir
def validate_module_structure(directory):
    files = os.listdir(directory)
    extension_file_mapping = {}
    for item in files:
        # check file extension and ensure that we have one python, one JSON,
        # and optionally one HTML file.

        # Skip directories (__pycache__ etc.) and test_*
        if not os.path.isdir(item) and not item.startswith('test'):
            if item in ['__init__.py', 'setup.py', 'package.json',
                        'package-lock.json']:
                continue

            extension = item.rsplit('.', 1)
            if len(extension) > 1:
                extension = extension[1]
            else:
                continue
            if extension in ["py", "json", "html", "js"]:
                if extension not in extension_file_mapping:
                    extension_file_mapping[extension] = item
                else:
                    raise ValidationError(
                        f'Multiple files exist with extension {extension}.'
                        f" This isn't currently supported."
                    )

    if 'json' not in extension_file_mapping:
        raise ValidationError('Missing ".json" module-spec file')
    if 'py' not in extension_file_mapping:
        raise ValidationError('Missing ".py" module-code file')

    return extension_file_mapping


# Now check if the module is importable and defines the render function
def validate_python_functions(destination_directory, python_file):
    # execute the module, as a test
    path = os.path.join(destination_directory, python_file)
    try:
        spec = importlib.util.spec_from_file_location('test', path)
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


# Directories that the module files go through as we load and validate them
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))  # path of this file
ROOT_DIRECTORY = os.path.dirname(CURRENT_PATH)
MODULE_DIRECTORY = os.path.join(ROOT_DIRECTORY, "importedmodules")


# Load a module after cloning from github
# This is the guts of our module import, also a good place to hook into for
# tests (bypassing github access). Returns a dictionary of info to display to
# user (category, repo name, author, id_name)
def import_module_from_directory(version, importdir, force_reload=False):
    # check that right files exist
    extension_file_mapping = validate_module_structure(importdir)
    python_file = extension_file_mapping['py']
    json_file = extension_file_mapping['json']
    js_file = extension_file_mapping.get('js')

    # load json file
    with open(os.path.join(importdir, json_file)) as f:
        try:
            module_config = json.load(f)
        except ValueError:
            raise ValidationError('Invalid JSON file')
    validate_module_spec(module_config)  # raises ValidationError
    validate_python_functions(importdir, python_file)

    id_name = module_config['id_name']

    destination_directory = os.path.join(MODULE_DIRECTORY, id_name, version)

    if force_reload:
        # Allow re-import. If files already exist, delete them so we can
        # overwrite them.
        #
        # This can race with module callers. Assuming we only force_reload
        # in dev/test, races won't harm anyone.
        try:
            shutil.rmtree(destination_directory)
        except FileNotFoundError:
            pass  # we aren't reloading after all -- this is a new version
    else:
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

    if js_file:
        with open(os.path.join(importdir, js_file), 'rt') as f:
            js_module = f.read()
    else:
        js_module = ''

    # Copy code into filesystem
    shutil.copytree(importdir, destination_directory)

    # If that succeeds, initialise module in our database
    module_version = ModuleVersion.create_or_replace_from_spec(
        module_config,
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

        try:
            # depth=1: do not clone entire repo -- just the latest commit
            repo = git.Repo.clone_from(url, importdir, depth=1)
        except GitCommandError as err:
            raise ValidationError(
                f'Unable to clone {url}: {str(err)}'
            )

        version = repo.head.commit.hexsha[:7]

        # Nix ".git" subdir: not a Git repo any more, just a dir
        shutil.rmtree(os.path.join(importdir, '.git'))

        return import_module_from_directory(version, importdir, force_reload)
