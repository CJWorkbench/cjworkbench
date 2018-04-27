from .initmodules import load_module_from_dict
from server.models import Module, ModuleVersion
from server.utils import log_message
from django.forms import URLField
from django.core.exceptions import ValidationError

import importlib.machinery
from importlib import import_module

import inspect
import json
import os
import re
import shutil
import sys

import time
import git
from git.exc import GitCommandError


# add /server to path -- needed?
cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_directory = os.path.dirname(cwd)
sys.path.insert(0, parent_directory)

categories = set()

# Categories allowed for modules. If not in this list, will be assigned "Other"
def get_categories():
    return ['Add data', 'Clean', 'Analyze', 'Code', 'Visualize']

# Returns dict of {id_name: url} for existing Module objects
def get_already_imported_module_urls():
    already_imported = dict()
    modules = Module.objects.all()
    for module in modules:
        already_imported[module.id_name] = module.link
    return already_imported

def refresh_module_from_github(url):
    #we should check if this is a refreshable module: does the module exist, and if it does,
    #...and if it is, we should import it.
    import_module_from_github(url)

def sanitise_url(url):
    if url.strip() == "":
        raise ValidationError("Empty URL entered.")
    # verify if this is a valid GitHub url
    url_form_field = URLField()
    try:
        url = url_form_field.clean(url)
        if "github" not in url:
            raise ValidationError('Invalid GitHub URL entered: %s' % (url))
        # - if entered url has a tailing '/', remove it
        if url[-1] == '/':
            url = url[:-1]
        # - strip out '.git' if it exists in the URL
        if url.endswith('.git'):
            url = url[0:-4]
        return url
    except ValidationError:
        raise ValidationError('Invalid GitHub URL entered: %s' % (url))

def retrieve_project_name(url):
    # - extract the folder name from the url
    return url.rsplit('/', 1)[1]

def retrieve_author(url):
    if url[-1] == '/':
        url = url[:-1]
    # - extract the account name from the url
    account = url.rsplit('/', 2)[1]
    return account

# Check that we have one .py and one .json file in the repo root dir
def validate_module_structure(directory):
    files = os.listdir(directory)
    if len(files) < 3:
        raise ValidationError('{} is not a valid workflow module.'.format(directory))

    extension_file_mapping = {}
    for item in files:
        # check file extension and ensure that we have one python, one JSON, and optionally one HTML file.

        # Skip directories (__pycache__ etc.) and test_*
        if not os.path.isdir(item) and not item.startswith('test'):
            extension = item.rsplit('.', 1)
            if len(extension) > 1:
                extension = extension[1]
            else:
                continue
            if extension in ["py", "json", "html"]:
                if extension not in extension_file_mapping:
                    if item not in '__init__.py':
                        extension_file_mapping[extension] = item
                else:
                    raise ValidationError(
                        "Multiple files exist with extension {}. This isn't currently supported.".format(extension))

    if len(extension_file_mapping) < 2:
        raise ValidationError(
            '{} is not a valid workflow module. You must have exactly one .py file and one .json file.'.format(
                directory))

    return extension_file_mapping


#  When the json file is loaded into a dict, it should contain the
#  following keys: name, id_name, category. Parameters are actually optional.
def get_module_config_from_json(url, extension_file_mapping, directory):
    try:
        json_file = extension_file_mapping['json']
    except KeyError:
        raise ValidationError("No JSON file found in remote repository.") # shouldn't happen, checked in validate_module_struture

    with open(os.path.join(directory, json_file)) as readable:
        try:
            module_config = json.load(readable)
        except json.decoder.JSONDecodeError as e:
            raise ValidationError('{} of {}'.format(str(e), json_file))

    if "name" not in module_config or "id_name" not in module_config or "category" not in module_config:
        raise ValidationError("The module configuration isn't in the correct format. It should contain name, id_name, "
                      "category and parameters")

    return module_config

# Where this version of this module actually lives. Filed under importedmodules/reponame/git_version_hash
def destination_directory_name(reponame, version):

    # check if files with the same name already exist.
    # This can happen if a module is deleted from the server DB, then re-imported
    # Just delete existing if so
    destination_directory = os.path.join(MODULE_DIRECTORY, reponame, version)
    if os.path.isdir(destination_directory):
        shutil.rmtree(destination_directory)

    return destination_directory


# Move py and json files to the directory where they will live henceforth
# that's /importedmodules/projname/version
def move_files_to_final_location(destination_directory, curdir, json_file, python_file, html_file=None):

    try:
        os.makedirs(destination_directory)
        shutil.move(os.path.join(curdir, json_file), os.path.join(destination_directory, json_file))
    except (OSError, Exception) as error:
        raise ValidationError("Unable to move JSON file to module directory: {}.".format(error))

    try:
        shutil.move(os.path.join(curdir, python_file),
                  os.path.join(destination_directory, python_file))
    except (OSError, Exception) as error:
        raise ValidationError("Unable to move Python file to module directory.")

    if html_file:
        try:
            shutil.move(os.path.join(curdir, html_file),
                      os.path.join(destination_directory, html_file))
        except (OSError, Exception) as error:
            raise ValidationError("Unable to move HTML file to module directory.")


# adds two spaces before every line
def indent_lines(str):
    return '  ' + str.replace('\n', '\n  ');


module_boilerplate = """
import numpy as np
import pandas as pd
from io import StringIO
import re

class Importable:
  @staticmethod
  def __init__(self):
    pass

  @staticmethod
"""

# Convert line numbers in our imported module code back to line numbers in the original file
# For the poor module writers
def original_module_lineno(line):
    return line - module_boilerplate.count('\n')


# Ensure the Python file compiles
# This function rewrites the file to add module definition boilerplate.
def add_boilerplate_and_check_syntax(destination_directory, python_file):


    filename = os.path.join(destination_directory, python_file)

    try:
        script = open(os.path.join(filename), 'r').read() + '\n'
    except:
        raise ValidationError("Unable to open Python code file {}.".format(python_file))

    # Indent the user's function declaration to put it inside the Importable class, then replace file contents
    script = module_boilerplate + indent_lines(script)
    sfile = open(os.path.join(filename), 'w')
    sfile.write(script)
    sfile.close()

    try:
        compiled = compile(script, filename, 'exec')  # filename used only for stack traces etc.
        if compiled == None:
            raise ValidationError("Empty Python code file.")
    except ValueError:
        raise ValidationError("Source file {} contains bad characters.".format(python_file))
    except SyntaxError as se:
        # We have to change the reported line number to account for our boilerplate
        errstr = str(se)
        linenostr = re.search('line (\d+)', errstr).group(1)
        newlineno = original_module_lineno(int(linenostr))
        newstr = errstr.replace(linenostr, str(newlineno))
        raise ValidationError(newstr)

    return compiled


# Now check if the module is importablr and defines the render function
def validate_python_functions(destination_directory, python_file):
    p, m = python_file.rsplit(".", 1)

    # We need to reinsert the path so that the imported module can be read. :/
    # OK, the time.sleep is weird, but it seems to circumvent the issue where we get an error
    # "ImportError: No module named ..." probably because of a race condition/the time it takes for the system to
    # recognise the insert of the new path. There's probably a better solution though?
    sys.path.insert(0, destination_directory)
    time.sleep(2)
    imported_module = import_module(p)
    imported_class = inspect.getmembers(imported_module, inspect.isclass)

    try:
        imported_class = imported_class[0]
        if not callable(imported_class[1].render):
            raise ValidationError("Module render() function isn't callable.")
    except:
        raise ValidationError("Module render() function is missing.")

    return imported_class


# Get head version hash from git repo on disk
def extract_version(repodir):
    repo = git.Repo(repodir)
    version = repo.head.object.hexsha[:7]
    return version


# Directories that the module files go through as we load and validate them
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__)) # path of this source file
ROOT_DIRECTORY = os.path.dirname(CURRENT_PATH)
MODULE_DIRECTORY = os.path.join(ROOT_DIRECTORY, "importedmodules")


# Load a module after cloning from github
# This is the guts of our module import, also a good place to hook into for tests (bypassing github access)
# Returns a dictionary of info to display to user (category, repo name, author, id_name)
def import_module_from_directory(url, reponame, version, importdir):

    destination_directory = None
    ui_info = {}

    try:
        # check that right files exist
        extension_file_mapping = validate_module_structure(importdir)
        python_file = extension_file_mapping['py']
        json_file = extension_file_mapping['json']
        html_file = extension_file_mapping.get('html', None)

        module_config = get_module_config_from_json(url, extension_file_mapping, importdir)
        id_name = module_config['id_name']

        # Don't allow importing the same version twice
        if ModuleVersion.objects.filter(module__id_name=id_name, source_version_hash=version):
            raise ValidationError('Version {} of module {} has already been imported'.format(version, url))

        # Don't allow loading a module with the same id_name from a different repo.
        module_urls = get_already_imported_module_urls()
        if module_config["id_name"] in module_urls and url != module_urls[module_config["id_name"]]:
            source = module_urls[module_config["id_name"]]
            if source == '':
                source = "Internal"
            raise ValidationError(
                "Module {} has already been loaded, and its source is {}.".format(module_config["id_name"], source))

        module_config["source_version"] = version
        module_config["link"] = url
        module_config["author"] = module_config["author"] if "author" in module_config else retrieve_author(url)

        # Ensure that modules are categorised properly – if a module category isn't one of our
        # pre-defined categories, then we just set it to other.
        if module_config["category"] not in get_categories():
            module_config["category"] = "Other"

        # The core work of creating a module
        destination_directory = destination_directory_name(id_name, version)
        move_files_to_final_location(destination_directory, importdir, json_file, python_file, html_file=html_file)
        add_boilerplate_and_check_syntax(destination_directory, python_file)
        validate_python_functions(destination_directory, python_file)

        # actually import the module into our Python environment, as  test -- dynamicdispatch will load as needed
        temp = importlib.machinery.SourceFileLoader(os.path.join(destination_directory, python_file),
                                                    os.path.join(destination_directory, python_file)).load_module()
        globals().update(temp.__dict__)

        # If that succeeds, initialise module in our database
        load_module_from_dict(module_config)

        # clean-up
        shutil.rmtree(importdir)

        # data that we probably want displayed in the UI.
        ui_info["category"] = module_config["category"]
        ui_info["project"] = reponame
        ui_info["author"] = module_config["author"]
        ui_info["name"] = module_config["name"]

    except Exception as e:
        log_message('Error importing module %s: %s' % (url, str(e)))
        if destination_directory is not None:
            try:
                shutil.rmtree(destination_directory)
            except:
                pass
        raise

    return ui_info


# Top level import, clones from github
def import_module_from_github(url):

    url = url.lower().strip()
    url = sanitise_url(url)

    reponame = retrieve_project_name(url)
    importdir = os.path.join(MODULE_DIRECTORY, 'clones', reponame)

    # Delete anything that might left over junk from previous failures (shouldn't happen, but)
    if  os.path.isdir(importdir):
        shutil.rmtree(importdir)

    try:
        # pull contents from GitHub
        try:
            git.Repo.clone_from(url, importdir)

        except (ValidationError, GitCommandError) as ve:
            if type(ve) == GitCommandError:
                message = "Received Git error status code {}".format(ve.status)
            else:
                message = ve.message
            raise ValidationError('Unable to clone from GitHub: %s' % (url) +
                                  ': %s' % (message))

        # retrieve Git hash to use as the version number.
        version = extract_version(importdir)

        ui_info = import_module_from_directory(url, reponame, version, importdir)


    except Exception as e:
        # Clean up any existing dirs and pass exception up (ValidationErrors will have error message for user)
        if os.path.isdir(importdir):
            shutil.rmtree(importdir)
        raise

    log_message('Successfully imported module %s' % url)
    return ui_info
