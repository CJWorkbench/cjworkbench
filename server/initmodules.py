# Initialize the list of available modules on startup
# For the moment, this consists of loading them from json files at startup

import os
import json
from cjworkbench.settings import BASE_DIR
from server.models import Module, ModuleVersion, WfModule, ParameterSpec, ParameterVal

import logging
logger = logging.getLogger(__name__)

class InitModuleError(Exception):
    pass

# Top level call, (re)load module definitions from files.
# Raises on error.
def init_modules():
    module_path = os.path.join(BASE_DIR, 'server/modules')

    # Get all json files in this directory (exclude dirs)
    modfiles = [f for f in os.listdir(module_path) if os.path.isfile(os.path.join(module_path, f)) and f.endswith(".json")]

    # Load all modules from files
    for f in modfiles:
        try:
            load_module_from_file(os.path.join(module_path, f))
        except ValueError as e:
            logger.error(
                "Error loading Module definition file %s: %s",
                f,
                str(e)
            )
            raise InitModuleError() from e

    logger.info('Loaded %d modules', len(modfiles))


# Create a module object by reading in the json description in a file
def load_module_from_file(fname):
    logger.info("Loading module " + fname)

    with open(fname) as json_data:
        d = json.load(json_data)
        load_module_from_dict(d)


# Create a module from dictionary of properties, corresponding to the json in the config file
# testable entrypoint
# returns Module
def load_module_from_dict(d):
    required = ['name', 'id_name', 'category']
    for x in required:
        if not x in d:
            raise ValueError("Module specification missing field " + x)

    id_name = d['id_name']

    # If we can find an existing module with the same id_name, use that
    matches = Module.objects.filter(id_name=id_name)
    if len(matches)>0:
        assert (len(matches) == 1)  # no duplicates please
        module = matches[0]
    else:
        module = Module()

    # save module data
    module.name = d['name']
    module.category = d['category']
    module.id_name = id_name
    module.dispatch = id_name
    module.source = d.get('source', '')
    module.description = d.get('description', '')
    module.author = d.get('author', 'Workbench')
    module.link = d.get('link', '')
    module.icon = d.get('icon', 'settings')
    module.loads_data = d.get('loads_data', False)
    module.help_url = d.get('help_url', '')

    module.save()

    #add module.last_updated here.
    source_version = d.get('source_version', '1.0')
    version_matches = ModuleVersion.objects.filter(module=module, source_version_hash = source_version)

    if len(version_matches) > 0:
        assert (len(version_matches) == 1)  # no duplicates please
        module_version = version_matches[0]
    else:
        module_version = ModuleVersion()

    module_version.source_version_hash = source_version
    # the last_update_time should automatically be added based on _now_.
    # possible todo: should this be driven based on the last_commit time or the last system time?
    module_version.module = module

    module_version.html_output = d.get('html_output', False)

    module_version.save()

    # load params
    if 'parameters' in d:
        pspecs = [ load_parameter_spec(p, module_version, order) for (order,p) in enumerate(d['parameters']) ]
    else:
        pspecs = []

    # delete all ParameterSpecs (and hence ParameterVals) for this module that were not in the new module description
    for ps in ParameterSpec.objects.filter(module_version=module_version):
        if ps not in pspecs: # relies on model == comparing id field
            ps.delete()

    return module_version


# Load parameter spec from json def
# If it's a brand new parameter spec, add it to all existing WfModules
# Otherwise re-use existing spec object, and update all existing ParameterVal objects that point to it
# returns ParameterSpec
def load_parameter_spec(d, module_version, order):

    # minimally required fields
    required = ['name', 'id_name', 'type']
    for x in required:
        if not x in d:
            raise ValueError("Parameter specification missing field " + x)

    name = d['name']
    id_name = d['id_name']
    ptype = d['type']

    # Is this type recognized?
    if ptype not in ParameterSpec.TYPES:
        raise ValueError("Unknown parameter type " + ptype)

    # Find any previous parameter specs with this id_name (including any we just loaded)
    oldspecs =  ParameterSpec.objects.filter(id_name=id_name, module_version=module_version)
    if len(oldspecs)>0:
        assert(len(oldspecs))==1  # ids should be unique
        pspec = oldspecs[0]
        pspec.name = name
        type_changed = pspec.type != ptype
        pspec.type = ptype
        reloading = True
    else:
        pspec = ParameterSpec(name=name, id_name=id_name, type=ptype, module_version=module_version)
        reloading = False

    if 'default' in d:
        pspec.def_value = d['default']
    else:
        pspec.def_value = ''        # ParameterVal.set_value will translate to 0, false, etc. according to type

    if d['type'] == 'menu':
        if (not 'menu_items' in d) or (d['menu_items']==''):
            raise ValueError("Menu parameter specification missing menu_items")
        pspec.def_menu_items = d['menu_items']

    pspec.def_visible = d.get('visible', True)
    pspec.ui_only = d.get('ui-only', False)
    pspec.multiline = d.get('multiline', False)
    pspec.derived_data = d.get('derived-data', False)
    pspec.placeholder = d.get('placeholder', '')

    # For inversion, use the 'invert' attribute here
    if 'visible_if' in d:
        if 'id_name' in d['visible_if'] and 'value' in d['visible_if']:
            pspec.visible_if = json.dumps(d.get('visible_if', {}))
        else:
            raise ValueError('visible_if must have "id_name" and "value" attributes')

    pspec.order = order
    pspec.save()

    # if parameter is newly added, add new ParameterVals to all existing modules
    if not reloading:
        for wfm in WfModule.objects.filter(module_version=module_version):
            pval = ParameterVal.objects.create(wf_module=wfm, parameter_spec=pspec)
            pval.init_from_spec()
            pval.save()

    # If the parameter is reloading, reset order in UI. If type also changed, reset existing value to default
    if reloading:
        for pval in ParameterVal.objects.filter(parameter_spec=pspec):
            pval.order = pspec.order
            if type_changed:
                pval.init_from_spec()
            pval.save()

    return pspec
