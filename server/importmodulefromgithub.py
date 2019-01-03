import importlib.util
import json
import logging
import os
import re
import shutil
from django.forms import URLField
from django.core.exceptions import ValidationError
import git
from git.exc import GitCommandError
from server.models import ModuleVersion
from server.models.module_version import validate_module_spec


logger = logging.getLogger(__name__)


def sanitise_url(url):
    url = url.strip()
    if not url:
        raise ValidationError("Empty URL")

    if 'http://git-server/' in url:
        # integration tests
        return url

    try:
        url = URLField().clean(url)
    except ValidationError:
        raise ValidationError('Invalid Git repo URL entered: %s' % (url))

    return url


def retrieve_project_name(url):
    # - extract the folder name from the url
    return url.rsplit('/', 1)[1]


# Check that we have one .py and one .json file in the repo root dir
def validate_module_structure(directory):
    files = os.listdir(directory)
    if len(files) < 3:
        raise ValidationError(f'{directory} is not a valid workflow module')

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

    if len(extension_file_mapping) < 2:
        raise ValidationError(
            f'{directory} is not a valid module.',
            f' You must have exactly one .py file and one .json file'
        )

    return extension_file_mapping


#  When the json file is loaded into a dict, it should contain the
#  following keys: name, id_name, category. Parameters are actually optional.
def get_module_config_from_json(url, extension_file_mapping, directory):
    try:
        json_file = extension_file_mapping['json']
    except KeyError:
        # shouldn't happen, checked in validate_module_struture
        raise ValidationError("No JSON file found in remote repository.")

    with open(os.path.join(directory, json_file)) as readable:
        try:
            module_config = json.load(readable)
        except json.decoder.JSONDecodeError as e:
            raise ValidationError('{} of {}'.format(str(e), json_file))

    if "name" not in module_config \
       or "id_name" not in module_config \
       or "category" not in module_config:
        raise ValidationError(
            "The module configuration isn't in the correct format."
            ' It should contain name, id_name, category and parameters.'
        )

    return module_config


# Directory where this version of this module actually lives.
# Filed under importedmodules/reponame/git_version_hash
def create_destination_directory(reponame, version):
    # check if files with the same name already exist.
    # This can happen if a module is deleted from the server DB, then
    # re-imported. Just delete existing if so.
    destination_directory = os.path.join(MODULE_DIRECTORY, reponame, version)
    if os.path.isdir(destination_directory):
        shutil.rmtree(destination_directory)
    os.makedirs(destination_directory)
    original_dir = destination_directory + '-original'
    if os.path.isdir(original_dir):
        shutil.rmtree(original_dir)
    os.makedirs(original_dir)

    return destination_directory


# Move py,json,html files to the directory where they will live henceforth
# that's /importedmodules/projname/version for the mangled ones (with
# boilerplate) that we run plus /importedmodules/projname/version-original for
# the pristine source files (so we can change boilerplate)
def move_files_to_final_location(destination_directory, imported_dir, files):
    original_dir = destination_directory + '-original'

    for f in files:
        if f:  # html or other optional files might be None
            try:
                shutil.copy(
                    os.path.join(imported_dir, f),
                    os.path.join(original_dir, f)
                )
            except (OSError, Exception) as error:
                raise ValidationError(
                    f'Unable to copy {f} to module directory: {str(error)}'
                )

            try:
                shutil.move(
                    os.path.join(imported_dir, f),
                    os.path.join(destination_directory, f)
                )
            except (OSError, Exception) as error:
                raise ValidationError(
                    f'Unable to move {f} to module directory:{str(error)}'
                )


module_boilerplate = """
import numpy as np
import pandas as pd
from io import StringIO
import re

"""


# Convert line numbers in our imported module code back to line numbers in
# the original file, For the poor module writers.
def original_module_lineno(line):
    return line - module_boilerplate.count('\n')


# Ensure the Python file compiles
# This function rewrites the file to ADD STEP definition boilerplate.
def add_boilerplate_and_check_syntax(destination_directory, python_file):
    filename = os.path.join(destination_directory, python_file)

    try:
        script = open(os.path.join(filename), 'r').read() + '\n'
    except Exception:  # TODO what exception?
        raise ValidationError(f'Unable to open Python code file {python_file}')

    # Indent the user's function declaration to put it inside the Importable
    # class, then replace file contents
    script = module_boilerplate + script
    sfile = open(os.path.join(filename), 'w')
    sfile.write(script)
    sfile.close()

    try:
        # filename used only for stack traces etc.
        compiled = compile(script, filename, 'exec')
        if compiled is None:
            raise ValidationError('Empty Python code file.')
    except ValueError:
        raise ValidationError(
            'Source file {python_file} contains bad characters'
        )
    except SyntaxError as se:
        # Change the reported line number to account for our boilerplate
        errstr = str(se)
        linenostr = re.search('line (\\d+)', errstr).group(1)
        newlineno = original_module_lineno(int(linenostr))
        newstr = errstr.replace(linenostr, str(newlineno))
        raise ValidationError(newstr)

    return compiled


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


# Get head version hash from git repo on disk
def extract_version(repodir):
    repo = git.Repo(repodir)
    version = repo.head.object.hexsha[:7]
    return version


# Directories that the module files go through as we load and validate them
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))  # path of this file
ROOT_DIRECTORY = os.path.dirname(CURRENT_PATH)
MODULE_DIRECTORY = os.path.join(ROOT_DIRECTORY, "importedmodules")


# Load a module after cloning from github
# This is the guts of our module import, also a good place to hook into for
# tests (bypassing github access). Returns a dictionary of info to display to
# user (category, repo name, author, id_name)
def import_module_from_directory(url, reponame, version, importdir,
                                 force_reload=False):
    destination_directory = None

    try:
        # check that right files exist
        extension_file_mapping = validate_module_structure(importdir)
        python_file = extension_file_mapping['py']
        json_file = extension_file_mapping['json']
        html_file = extension_file_mapping.get('html', None)
        js_file = extension_file_mapping.get('js', None)

        # load json file
        module_config = get_module_config_from_json(url,
                                                    extension_file_mapping,
                                                    importdir)
        validate_module_spec(module_config)  # raises ValidationError
        id_name = module_config['id_name']

        # Don't allow importing the same version twice, unless forced
        if not force_reload:
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

        # The core work of creating a module
        destination_directory = create_destination_directory(id_name, version)
        move_files_to_final_location(destination_directory, importdir,
                                     [json_file, python_file, html_file])
        add_boilerplate_and_check_syntax(destination_directory, python_file)
        validate_python_functions(destination_directory, python_file)

        # If that succeeds, initialise module in our database
        module_version = ModuleVersion.create_or_replace_from_spec(
            module_config,
            source_version_hash=version,
            js_module=js_module
        )

        # clean-up
        shutil.rmtree(importdir)

        return module_version
    except Exception:
        # On exception, clean up and raise
        if destination_directory:
            try:
                shutil.rmtree(destination_directory)
            except FileNotFoundError:
                pass

            try:
                shutil.rmtree(destination_directory + '-original')
            except FileNotFoundError:
                pass

        raise


# Top level import, clones from github
# If force_relaod, reloads the module even if the version hasn't changed
# (normally, this is an error). On success, returnd a dict with (category,
# repo name, author, id_name) to tell user what happened
def import_module_from_github(url, force_reload=False):
    url = sanitise_url(url)

    reponame = retrieve_project_name(url)
    importdir = os.path.join(MODULE_DIRECTORY, 'clones', reponame)

    # Delete anything that might left over junk from previous failures
    # (shouldn't happen, but)
    if os.path.isdir(importdir):
        shutil.rmtree(importdir)

    try:
        # pull contents from GitHub
        try:
            git.Repo.clone_from(url, importdir)
        except GitCommandError as err:
            raise ValidationError(
                f'Received Git error status code {err.status}'
            )
        except ValidationError as err:
            raise ValidationError(
                f'Unable to clone from GitHub: {url}: {str(err)}'
            )

        # load it
        version = extract_version(importdir)
        module = import_module_from_directory(url, reponame, version,
                                              importdir, force_reload)

        logger.info('Imported module %s' % url)

        return module
    except Exception:
        # Clean up any existing dirs and pass exception up
        # (ValidationErrors will have error message for user)
        if os.path.isdir(importdir):
            shutil.rmtree(importdir)
        raise
