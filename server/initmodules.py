# Initialize the list of available modules on startup
# For the moment, this consists of loading them from json files at startup

import os
import json
from cjworkbench.settings import BASE_DIR
from server.models import Module, ParameterSpec, ParameterVal

import logging
logger = logging.getLogger(__name__)

# Top level call, blow away all modules and load new defintions from files
def init_modules():
    print("init modules")
    module_path = os.path.join(BASE_DIR, 'config/modules')

    # Get all json files in this directory (exclude dirs)
    modfiles = [f for f in os.listdir(module_path) if os.path.isfile(os.path.join(module_path, f)) and f.endswith(".json")]

    # Now the real fun begins. Delete all modules, load them from files
    Module.objects.all().delete()
    ParameterSpec.objects.all().delete()
    for f in modfiles:
        load_module(os.path.join(module_path, f))


# Create a module object by reading in the json description
# Create associated ParameterSpec objects too
def load_module(fname):

    print("Loading module " + fname)

    with open(fname) as json_data:

        # Skip unloadable modules
        try:
            d = json.load(json_data)

            if not 'name' in d:
                raise ValueError("Missing module name")
            if not 'internal_name' in d:
                raise ValueError("Missing module internal_name")

            module = Module(name=d['name'], internal_name=d['internal_name'], dispatch=d['internal_name'])
            module.save()

            if 'parameters' in d:
                pspecs = [ load_parameter_spec(p, module) for p in d['parameters']]
            else:
                pspecs = []

        except ValueError as e:
            logger.error("Error loading Module definition file " + fname + ": " + str(e))


# Create a single ParameterSpec object from json def
# Must pass in parent module
def load_parameter_spec(d, module):

    if not 'name' in d:
        raise ValueError("Missing parameter name")
    name = d['name']

    if d['type'] == 'string':
        p = ParameterSpec(type=ParameterSpec.STRING, name=name, module=module, def_string=d['default'], def_number=0, def_text='')

    elif d['type'] == 'number':
        p = ParameterSpec(type=ParameterSpec.NUMBER, name=name, module=module, def_string='', def_number=d['default'], def_text='')

    elif d['type'] == 'text':
        p = ParameterSpec(type=ParameterSpec.TEXT   , name=name, module=module, def_string='', def_number=0, def_text=d['default'])

    elif d['type'] != None:
        raise ValueError("Unknown parameter type " + d['type'])
    else:
        raise ValueError("Missing parameter type")

    p.save()
    return p


