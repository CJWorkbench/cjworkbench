from .initmodules import load_module_from_dict

from django.forms import URLField
from django.core.exceptions import ValidationError

import importlib.machinery
from importlib import import_module
import inspect
import json
import os
import shutil
import sys

import git

#OK, this feels wrong (and probably is wrong), but there's nowhere else that I can see we have all the module names and
#their corresponding classes. We need this to ensure that there are no clashes, and consequently, to ensure that we
#don't inadvertently override a valid, existing class with the import.

cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_directory = os.path.dirname(cwd)
sys.path.insert(0, parent_directory)

def import_module_from_github(url):
    url = url.lower().strip()

    # verify if this is a valid GitHub url
    url_form_field = URLField()
    try:
        url = url_form_field.clean(url)
        if "github" not in url:
            raise ValidationError
    except ValidationError:
        print('Invalid GitHub URL entered: %s' % (url))
        raise ValidationError('Invalid GitHub URL entered: %s' % (url))

    # extract directory/project name
    # - if entered url has a tailing '/', remove it
    if url[-1] == '/':
        url = url[:-1]
    # - extract the folder name from the url
    directory = url.rsplit('/', 1)[1]
    # - strip out '.git' if it exists in the URL
    if directory.endswith('.git'):
        directory = directory[0:-4]

    current_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    root_directory = os.path.dirname(current_path)

    # pull contents from GitHub
    try:
        git.Git().clone(url)
        # move this to correct directory, i.e. where this file is.
        os.rename(os.path.join(root_directory, directory), os.path.join(current_path, directory))
    except:
        print('Unable to pull down content from GitHub: %s' % (url))
        shutil.rmtree(os.path.join(root_directory, directory))
        raise ValidationError('Unable to pull down content from GitHub: %s' % (url))

    #retrieve Git hash to use as the version number.
    repo = git.Repo(search_parent_directories=True)
    version = repo.head.object.hexsha[:7]

    # check that all the files we need exist, and if so, validate them.
    # - get a list of all the file name
    files = os.listdir(os.path.join(current_path, directory))
    if len(files) < 3:
        shutil.rmtree(os.path.join(root_directory, directory))
        print('{} is not a valid workflow module'.format(directory))
        raise ValidationError('{} is not a valid workflow module'.format(directory))

    extension_file_mapping = {}
    for item in files:
        # check file extension and ensure that we have at least one python file, one JS file and one JSON file.
        extension = item.rsplit('.', 1)[1]
        if extension in ["py", "json"]:
            if extension not in extension_file_mapping:
                if item not in '__init__.py':
                    extension_file_mapping[extension] = item
            else:
                shutil.rmtree(os.path.join(current_path, directory))
                print( "Multiple files exist with extension {}. This isn't currently supported.".format(extension))
                raise ValidationError(
                    "Multiple files exist with extension {}. This isn't currently supported.".format(extension))

    if len(extension_file_mapping) < 2:
        shutil.rmtree(os.path.join(current_path, directory))
        print('{} is not a valid workflow module. You must have at least one .py file, one .js file and one .json file'.format(directory))
        raise ValidationError(
            '{} is not a valid workflow module. You must have at least one .py file, one .js file and one .json file'.format(
                directory))

    # - there should only be one json file, and it should be in the format mandated by
    #  config/modules. Therefore, when the file is loaded into a dict, it should contain the
    #  following keys: name, id_name, category, parameters. Parameters should have a length
    #  of at least 1, and the dict within should contain keys name, id_name, type.
    try:
        json_file = extension_file_mapping['json']
    except KeyError:
        shutil.rmtree(os.path.join(current_path, directory))
        print("No JSON file found in remote repository.")
        raise ValidationError("No JSON file found in remote repository.")

    with open(os.path.join(current_path, directory, json_file)) as readable:
        module_config = json.load(readable)
    if "name" not in module_config or "id_name" not in module_config or "category" not in module_config or \
                    "parameters" not in module_config:
        shutil.rmtree(os.path.join(current_path, directory))
        print("The module configuration isn't in the correct format. It should contain name, id_name, "
                      "category and parameters")
        raise ValidationError("The module configuration isn't in the correct format. It should contain name, id_name, "
                      "category and parameters")

    module_name = module_config["name"]
    # Check if we've already loaded a module with the same name.
    # Possible TODO: We might want to make this more intelligent, so that users can refresh the modules from here.
    # However, blindly overriding modules might be dangerous, because well, it could lead to unexpected
    # behaviour.
    if "server.modules." + module_name in sys.modules:
        shutil.rmtree(os.path.join(current_path, directory))
        print("A module named {} is already loaded.".format(module_name))
        raise ValidationError("A module named {} is already loaded.".format(module_name))

    #Initialise module
    load_module_from_dict(module_config)

    # validate python: first we ensure there's at least one python file, and then we check to see if there's _only_
    # one file, to cater for ambiguity.
    # Again, something that we might want to rethink – maybe dictate what the main python script should be called –
    # as breaking up a module into smaller scripts _should be_ perfectly legal. But, then, iterating through multiple
    # scripts may make this process slow.
    try:
        python_file = extension_file_mapping['py']
    except KeyError:
        shutil.rmtree(os.path.join(current_path, directory))
        print("No Python file found in remote repository.")
        raise ValidationError("No Python file found in remote repository.")

    #check if files with the same name already exist
    destination_json_directory = os.path.join(root_directory, "config/modules/", directory, version)
    destination_python_directory = os.path.join(current_path, "modules", directory, version)
    if os.path.isdir(destination_json_directory) or os.path.isdir(destination_python_directory):
        shutil.rmtree(os.path.join(current_path, directory))
        print("Files for this repository and this version already exist.")
        raise ValidationError("Files for this repository and this version already exist.")

    #if they don't, we can start organising our workspace.
    try:
        os.makedirs(destination_json_directory)
        os.rename(os.path.join(current_path, directory, json_file), os.path.join(destination_json_directory, json_file))
    except (OSError, Exception) as error:
        shutil.rmtree(os.path.join(current_path, directory))
        shutil.rmtree(destination_json_directory)
        print("Unable to move JSON file to correct directory: {}.".format(error))
        raise ValidationError("Unable to move JSON file to correct directory: {}.".format(error))

    try:
        os.makedirs(destination_python_directory)
        os.rename(os.path.join(current_path, directory, python_file), os.path.join(destination_python_directory, python_file))
    except (OSError, Exception) as error:
        shutil.rmtree(os.path.join(current_path, directory))
        shutil.rmtree(destination_json_directory)
        shutil.rmtree(destination_python_directory)
        print("Unable to move Python file to correct directory: {}".format(error))
        raise ValidationError("Unable to move Python file to correct directory.")

    # Now compile the file to ensure that it's a valid script.
    try:
        script = open(os.path.join(destination_python_directory, python_file), 'r').read() + '\n'
    except:
        shutil.rmtree(os.path.join(destination_python_directory))
        shutil.rmtree(os.path.join(destination_json_directory))
        shutil.rmtree(os.path.join(current_path, directory))
        print("Unable to open {}.".format(python_file))
        raise ValidationError("Unable to open {}.".format(python_file))

    try:
        compiled = compile(script, python_file, 'exec')
    except:
        shutil.rmtree(os.path.join(destination_python_directory))
        shutil.rmtree(os.path.join(destination_json_directory))
        shutil.rmtree(os.path.join(current_path, directory))
        print("Unable to compile {}.".format(python_file))
        raise ValidationError("Unable to compile {}.".format(python_file))

    # Now check if the functions we need exist, i.e. event and render
    p, m = python_file.rsplit(".", 1)
    # We need to reinsert the path so that the imported module can be read. :/
    sys.path.insert(0, destination_python_directory)
    imported_module = import_module(p)
    imported_class = inspect.getmembers(imported_module, inspect.isclass)
    if len(imported_class) > 1:
        shutil.rmtree(os.path.join(destination_python_directory))
        shutil.rmtree(os.path.join(current_path, directory))
        shutil.rmtree(os.path.join(destination_json_directory))
        print("Multiple classes exist in python file.")
        raise ValidationError("Multiple classes exist in python file.")

    try:
        imported_class = imported_class[0]

        if not callable(imported_class[1].event) or not callable(imported_class[1].render):
            print("Functions event() and render() don't exist in the module.")
            raise ValidationError("Functions event() or render() doesn't exist aren't callable.")
    except:
        shutil.rmtree(os.path.join(destination_python_directory))
        shutil.rmtree(os.path.join(destination_json_directory))
        shutil.rmtree(os.path.join(current_path, directory))

        print("Functions event() and render() don't exist in the module.")
        raise ValidationError("Functions event() and render() don't exist in the module.")


    # Possible TODO: do we want to/need to change the entitlements/ownership on the file for infosec?

    # load dynamically
    temp = importlib.machinery.SourceFileLoader(os.path.join(destination_python_directory, python_file),
                                                os.path.join(destination_python_directory, python_file)).load_module()
    globals().update(temp.__dict__)

    shutil.rmtree(os.path.join(current_path, directory))

