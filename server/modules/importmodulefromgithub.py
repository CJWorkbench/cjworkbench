from .moduleimpl import ModuleImpl
from server.versions import bump_workflow_version

from django.forms import URLField
from django.core.exceptions import ValidationError

from collections import defaultdict
import importlib.machinery
from importlib import import_module
import inspect
import json
import os
import sys

import git

#OK, this feels wrong (and probably is wrong), but there's nowhere else that I can see we have all the module names and
#their corresponding classes. We need this to ensure that there are no clashes, and consequently, to ensure that we
#don't inadvertently override a valid, existing class with the import.

cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_directory = os.path.dirname(cwd)
sys.path.insert(0, parent_directory)


class ImportModuleFromGitHub(ModuleImpl):

    @staticmethod
    def event(parameter, e):
        wfm = parameter.wf_module
        try:
            url = wfm.get_param_string('url')
        except:
            wfm.set_error("No URL entered")
            return

        url = url.lower().strip()

        #verify if this is a valid GitHub url
        url_form_field = URLField()
        try:
            url = url_form_field.clean(url)
            if "github" not in url:
                raise ValidationError
        except ValidationError:
            wfm.set_error('Invalid GitHub URL entered: %s' % (url))
            return

        #extract directory/project name
        #- if entered url has a tailing '/', remove it
        if url[-1] == '/':
            url = url[:-1]
        #- extract the folder name from the url
        directory = url.rsplit('/', 1)[1]
        #- strip out '.git' if it exists in the URL
        if directory.endswith('.git'):
            directory = directory[0:-4]

        current_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        root_directory = os.path.dirname(os.path.dirname(current_path))

        #pull contents from GitHub
        try:
            git.Git().clone(url)
            #move this to correct directory, i.e. where this file is.
            os.rename(os.path.join(root_directory, directory), os.path.join(current_path, directory))
        except:
            wfm.set_error('Unable to pull down content from GitHub: %s' % (url))
            return

        #check that all the files we need exist, and if so, validate them.
        #- get a list of all the file name
        files = os.listdir(os.path.join(current_path, directory))
        if len(files) < 3:
            wfm.set_error('{} is not a valid workflow module'.format(directory))
            return

        extension_file_mapping = {}
        for item in files:
            #check file extension and ensure that we have at least one python file, one JS file and one JSON file.
            extension = item.rsplit('.', 1)[1]
            if extension in ["py", "js", "json"]:
                if extension not in extension_file_mapping:
                    if item not in '__init__.py':
                        extension_file_mapping[extension] = item
                else:
                    wfm.set_error("Multiple files exist with extension {}. This isn't currently supported.".format(extension))
                    return

        if len(extension_file_mapping) < 3:
            wfm.set_error('{} is not a valid workflow module. You must have at least one .py file, one .js file and one .json file'.format(directory))
            return

        #- there should only be one json file, and it should be in the format mandated by
        #  config/modules. Therefore, when the file is loaded into a dict, it should contain the
        #  following keys: name, id_name, category, parameters. Parameters should have a length
        #  of at least 1, and the dict within should contain keys name, id_name, type.
        try:
            json_file = extension_file_mapping['json']
        except KeyError:
            wfm.set_error("No JSON file found in remote repository.")
            return

        with open(os.path.join(current_path, directory, json_file)) as readable:
            module_config = json.load(readable)
        if "name" not in module_config or "id_name" not in module_config or "category" not in module_config or \
            "parameters" not in module_config:
            wfm.set_error("The module configuration isn't in the correct format. It should contain name, id_name, "
                          "category and parameters")
            return

        module_name = module_config["name"]
        #Check if we've already loaded a module with the same name.
        #Possible TODO: We might want to make this more intelligent, so that users can refresh the modules from here.
        #However, blindly overriding modules might be dangerous, because well, it could lead to unexpected
        #behaviour.
        if "server.modules." + module_name in sys.modules:
            wfm.set_error("A module named {} is already loaded.".format(module_name))
            return

        #Now, once we've determined that the module is loadable, let's ensure that the parameters match our
        #expectations. We iterate through all the params to do this, thereby validating that all parameters
        #are valid.
        parameters = module_config["parameters"]
        for item in parameters:
            if "name" not in item or "id_name" not in item or "type" not in item:
                wfm.set_error("The parameters for this model aren't clearly defined. At least one parameter currently" \
                              " only has keys {} whereas it needs id_name, name and type.".format(item.keys))
                return

        #validate python: first we ensure there's at least one python file, and then we check to see if there's _only_
        #one file, to cater for ambiguity.
        #Again, something that we might want to rethink – maybe dictate what the main python script should be called –
        #as breaking up a module into smaller scripts _should be_ perfectly legal. But, then, iterating through multiple
        #scripts may make this process slow.
        try:
            python_file = extension_file_mapping['py']
        except KeyError:
            wfm.set_error("No Python file found in remote repository.")
            return

        #Absolute path to where the Python file should be.
        absolute_python_file = os.path.join(current_path, python_file)

        os.rename(os.path.join(current_path, directory, json_file), os.path.join(root_directory, "config/modules/", json_file))
        os.rename(os.path.join(current_path, directory, python_file), absolute_python_file)

        #Now compile the file to ensure that it's a valid script.
        try:
            script = open(os.path.join(current_path, python_file), 'r').read() + '\n'
        except:
            wfm.set_error("Unable to open {}.".format(python_file))
            return

        try:
            compiled = compile(script, python_file, 'exec')
        except:
            wfm.set_error("Unable to compile {}.".format(python_file))
            return


        #Now check if the functions we need exist, i.e. event and render
        p, m = python_file.rsplit(".", 1)
        #We need to reinsert the path so that the imported module can be read. :/
        sys.path.insert(0, current_path)
        imported_module = import_module(p)
        imported_class = inspect.getmembers(imported_module, inspect.isclass)
        if len(imported_class) > 1:
            wfm.set_error("Multiple classes exist in python file.")
            return

        imported_class = imported_class[0]

        try:
            if not callable(imported_class[1].event) or not callable(imported_class[1].render):
                wfm.set_error("Functions event() or render() doesn't exist aren't callable.")
                return
        except:
            wfm.set_error("Functions event() and render() don't exist in the module.")
            return

        #system-level file clean-up (i.e. move files to correct directory and delete from root)
        #first, check if an external folder exists; if not create it and also touch __init__.py.
        if not os.path.isdir(os.path.join(current_path, "external")):
            try:
                os.makedirs(os.path.join(current_path, "external"))
            except:
                wfm.set_error("Unable to create directory to move the new module to.")
                return


        #Possible TODO: do we want to/need to change the entitlements/ownership on the file for infosec?

        #load dynamically
        temp = importlib.machinery.SourceFileLoader(absolute_python_file, absolute_python_file).load_module()
        globals().update(temp.__dict__)

        #Now, we need to make dispatch.py aware that a new module has been imported – there doesn't seem to be a nice,
        #elegant way of doing this.

        if wfm.status != wfm.ERROR:
            wfm.set_ready(notify=False)
            bump_workflow_version(wfm.workflow)
