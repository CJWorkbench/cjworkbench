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
            module = Module(name=d['name'])

            if 'parameters' in d:
                pspecs = [ load_parameter_spec(p, module) for p in d['parameters']]
            else:
                pspecs = []

            module.save()
        except ValueError as e:
            logger.error("Error loading Module definition file " + fname + ": " + str(e))



# Create a single ParameterSpec object from json def
# Must pass in parent module
def load_parameter_spec(d, module):

    if not 'name' in d:
        raise ValueError("Missing parameter name")

    defval = create_parameter_val_from_json(d)
    defval.save()

    if defval != None:
        return ParameterSpec(name=d['name'], default=defval, module=module)
    else:
        raise ValueError("Missing default parameter value")


# Instantiate a ParameterVal object, from name, type, default fields
def create_parameter_val_from_json(d):

    if d['type']=='string':
        p = ParameterVal(type=d['type'], string=d['default'], number=0, text='')

    elif d['type']=='number':
        p = ParameterSpec(type=d['type'], string='', number=d['default'], text='')

    elif d['type']=='text':
        p = ParameterVal(type=d['type'], string='', number=0, text=d['default'])

    elif d['type'] != None:
        raise ValueError("Unknown parameter type " + d['type'])

    else:
        raise ValueError("Missing parameter type")

    p.save()
    return p

