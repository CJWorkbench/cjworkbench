from .initmodules import load_module_from_dict
from server.models import Module

from django.forms import URLField
from django.core.exceptions import ValidationError

import importlib.machinery
from importlib import import_module

import inspect
import json
import os
import py_compile
import shutil
import sys
import time

import git
from git.exc import GitCommandError

#OK, this feels wrong (and probably is wrong), but there's nowhere else that I can see we have all the module names and
#their corresponding classes. We need this to ensure that there are no clashes, and consequently, to ensure that we
#don't inadvertently override a valid, existing class with the import.

cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_directory = os.path.dirname(cwd)
sys.path.insert(0, parent_directory)

categories = set()
already_imported = dict()

def get_categories():
    #cache categories
    if not categories:
        modules = Module.objects.all()
        for module in modules:
            categories.add(module.category)
        categories.add("Edit") #Ick, double ick, but hard-coding as a temporary measure.
        categories.add("Analyse")
    return categories

def get_already_imported():
    # cache modules already imported to ensure that we don't override existing modules
    if not already_imported:
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
        shutil.rmtree(os.path.join(root_directory, directory))
        raise ValidationError('{} is not a valid workflow module.'.format(directory))

    extension_file_mapping = {}
    for item in files:
        # check file extension and ensure that we have exactly one python file and one JSON file.
        if not os.path.isdir(item): # to make sure we don't get caught out by __pycaches__ and the like.
            extension = item.rsplit('.', 1)
            if len(extension) > 1:
                extension = extension[1]
            else:
                continue
            if extension in ["py", "json"]:
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
        module_config = json.load(readable)

    if "name" not in module_config or "id_name" not in module_config or "category" not in module_config:
        raise ValidationError("The module configuration isn't in the correct format. It should contain name, id_name, "
                      "category and parameters")

    # Check if we've already loaded a module with the same name.
    modules = get_already_imported()
    if module_config["id_name"] in modules and url != modules[module_config["id_name"]]:
        source = modules[module_config["id_name"]] if modules[module_config["id_name"]] != '' else "Internal"
        raise ValidationError("Module {} has already been loaded, and its source is {}.".format(module_config["id_name"], source))

    return module_config

# Where this version of this module actually lives
def destination_directory_name(moduledir, version):

    # check if files with the same name already exist.
    # This can happen if a module is deleted from the server DB, then re-imported
    # Just delete existing if so
    destination_directory = os.path.join(moduledir, version)
    if os.path.isdir(destination_directory):
        shutil.rmtree(destination_directory)

    return destination_directory


# Move py and json files to the directory where they will live henceforth
# that's /importedmodules/projname/version
def move_files_to_final_location(destination_directory, curdir, json_file, python_file):

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


# adds two spaces before every line
def indent_lines(str):
    return '  ' + str.replace('\n', '\n  ');

# Ensure the Python file compiles
# This function rewrites the file to add module definition boilerplate.
def add_boilerplate_and_check_syntax(destination_directory, python_file):

    boilerplate = """
import numpy as np
import pandas as pd

class Importable:
  @staticmethod
  def __init__(self):
    pass

  @staticmethod
"""

    filename = os.path.join(destination_directory, python_file)

    try:
        script = open(os.path.join(filename), 'r').read() + '\n'
    except:
        raise ValidationError("Unable to open Python code file {}.".format(python_file))

    # Indent the user's function declaration to put it inside the Importable class, then replace file contents
    script = boilerplate + indent_lines(script)
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
        raise ValidationError("{}: {}".format(python_file, str(se)))

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

#path of this file
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
#path of
ROOT_DIRECTORY = os.path.dirname(CURRENT_PATH)
MODULE_DIRECTORY = os.path.join(ROOT_DIRECTORY, "importedmodules")


def import_module_from_github(url):
    url = url.lower().strip()

    url = sanitise_url(url)

    projname = retrieve_project_name(url)
    tempdir = os.path.join(ROOT_DIRECTORY, projname)
    curdir = os.path.join(CURRENT_PATH, projname)
    moduledir = os.path.join(MODULE_DIRECTORY, projname)
    destination_directory = None
    message = {}

    try:
        # pull contents from GitHub
        try:
            git.Git().clone(url)

            # move this temporarily to where this source file is.
            shutil.move(tempdir, curdir)

        except (ValidationError, GitCommandError) as ve:
            if type(ve) == GitCommandError:
                message = "Received Git error status code {}".format(ve.status)
            else:
                message = ve.message
            raise ValidationError('Unable to clone from GitHub: %s' % (url) +
                                  ': %s' % (message))

        # retrieve Git hash to use as the version number.
        version = extract_version(curdir)

        # check that right files exist
        extension_file_mapping = validate_module_structure(curdir)
        python_file = extension_file_mapping['py']
        json_file = extension_file_mapping['json']

        module_config = get_module_config_from_json(url, extension_file_mapping, curdir)
        module_config["source_version"] = version
        module_config["link"] = url
        module_config["author"] = module_config["author"] if "author" in module_config else retrieve_author(url)

        # Ensure that modules are categorised properly – if a module category isn't one of our
        # pre-defined categories, then we just set it to other.
        if module_config["category"] not in get_categories():
            module_config["category"] = "Other"

        # The core work of creating a module
        destination_directory = destination_directory_name(moduledir, version)
        move_files_to_final_location(destination_directory, curdir, json_file, python_file)
        add_boilerplate_and_check_syntax(destination_directory, python_file)
        validate_python_functions(destination_directory, python_file)

        # Initialise module in our database
        load_module_from_dict(module_config)

        # Possible TODO: do we want to/need to change the entitlements/ownership on the file for infosec?

        # actually import the module into our Python environment
        temp = importlib.machinery.SourceFileLoader(os.path.join(destination_directory, python_file),
                                                    os.path.join(destination_directory, python_file)).load_module()
        globals().update(temp.__dict__)

        # clean-up
        shutil.rmtree(curdir)

        # data that we probably want displayed in the UI.
        message["category"] = module_config["category"]
        message["project"] = projname
        message["author"] = module_config["author"]
        message["name"] = module_config["name"]

    except Exception as e:
        # Clean up any existing dirs and pass exception up (ValidationErrors will have error message for user)
        try:
            shutil.rmtree(tempdir)
        except:
            pass
        try:
            shutil.rmtree(curdir)
        except:
            pass
        if destination_directory is not None:
            try:
                shutil.rmtree(destination_directory)
            except:
                pass
        raise

    return message
