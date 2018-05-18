# Initialize the list of available modules on startup
# For the moment, this consists of loading them from json files at startup

import os
import json
from cjworkbench.settings import BASE_DIR
from server.models import Module, ModuleVersion, WfModule, ParameterSpec, ParameterVal
from django.db import transaction

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
    try:
        module = Module.objects.get(id_name=id_name)
    except Module.DoesNotExist:
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

    if 'source_version' in d:
        module_version = ModuleVersion(source_version_hash=d['source_version'])
        module_version.module = module
        internal = False
    else:
        # This is an internal module. Re-use existing module_version if it exists
        try:
            module_version =  ModuleVersion.objects.get(module=module)
        except ModuleVersion.DoesNotExist:
            module_version = ModuleVersion(module=module, source_version_hash='1.0') # always 1.0 for internal modules
        internal = True

    module_version.html_output = d.get('html_output', False)
    module_version.save()

    # load params
    if 'parameters' in d:
        pspecs = [ load_parameter_spec(p, module_version, order) for (order,p) in enumerate(d['parameters']) ]
    else:
        pspecs = []

    # If we are re-using the module_version, delete all ParameterSpecs that were not in the new module description
    if internal:
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

    # If internal, get the spec for the same parameter from the previous module_version
    # Internal modules currently have only one version ever
    try:
        old_spec = ParameterSpec.objects.get(id_name=id_name, module_version__module=module_version.module)
    except ParameterSpec.DoesNotExist:
        old_spec = None

    pspec = ParameterSpec(name=name, id_name=id_name, type=ptype, module_version=module_version)

    # Optional keys
    pspec.def_value = d.get('default', '') # ParameterVal.set_value will translate to 0, false, etc. according to type
    pspec.def_visible = d.get('visible', True)
    pspec.ui_only = d.get('ui-only', False)
    pspec.multiline = d.get('multiline', False)
    pspec.derived_data = d.get('derived-data', False)
    pspec.placeholder = d.get('placeholder', '')

    if d['type'] == 'menu':
        if (not 'menu_items' in d) or (d['menu_items']==''):
            raise ValueError("Menu parameter specification missing menu_items")
        pspec.def_menu_items = d['menu_items']

    if 'visible_if' in d:
        if 'id_name' in d['visible_if'] and 'value' in d['visible_if']:
            pspec.visible_if = json.dumps(d.get('visible_if', {}))
        else:
            raise ValueError('visible_if must have "id_name" and "value" attributes')

    pspec.order = order
    pspec.save()

    # For internal modules, which are not versioned, we need to migrate all existing parameter vals to new spec
    update_parameter_vals_to_new_spec(old_spec, pspec)
    if old_spec:
        old_spec.delete()

    return pspec

# --- Parameter Spec migration ----
# Handles existing ParameterVals when a module's parameters change
# This can happen when reloading an internal module (because there is only one module_version)
# or when updating a WfModule to a new module_version

def create_parameter_val(wfm, new_spec):
    pval = ParameterVal.objects.create(wf_module=wfm, parameter_spec=new_spec)
    pval.init_from_spec()
    pval.save()


# Update a parameter value from one ParameterSpec to another. Resets to default if type changes.
def migrate_parameter_val(pval, old_spec, new_spec):
    type_changed = old_spec.type != new_spec.type
    pval.order = new_spec.order
    pval.parameter_spec = new_spec
    if type_changed:
        pval.init_from_spec()
    pval.save()


# Migrate parameter values on all existing WfModules to a new spec
# - If the parameter didn't exist before, add it
# - If the parameter has been removed, delete it
# - If the parameter changed:
#     - point existing vals to new spec
#     - set new order
#     - set to default value if the type changed
def update_parameter_vals_to_new_spec(old_spec, new_spec):

    if old_spec is None:
        # Added this parameter.
        if new_spec.module_version:
            # Update only if there are wfm that point to the new module version
            # (so not when we load a new version of an external module)
            for wfm in WfModule.objects.filter(module_version=new_spec.module_version):
                create_parameter_val(wfm, new_spec)

    elif new_spec is None:
        # Deleted this parameter
        ParameterVal.objects.filter(parameter_spec=old_spec).delete()

    else:
        # Changed this parameter
        for pval in ParameterVal.objects.filter(parameter_spec=old_spec):
            migrate_parameter_val(pval, old_spec, new_spec)


# Bump a module and all its existing ParameterVals to a new version of a module
def update_wfm_parameters_to_new_version(wfm, new_version):
    old_version = wfm.module_version

    if old_version != new_version:
        with transaction.atomic():

            # added or changed parameters
            for new_spec in ParameterSpec.objects.filter(module_version=new_version):
                try:
                    old_spec = ParameterSpec.objects.get(module_version=old_version, id_name=new_spec.id_name)
                    for pv in ParameterVal.objects.filter(wf_module=wfm, parameter_spec=old_spec):
                        migrate_parameter_val(pv, old_spec, new_spec)
                except ParameterSpec.DoesNotExist:
                    create_parameter_val(wfm, new_spec)

            # deleted parameters
            for old_spec in ParameterSpec.objects.filter(module_version=old_version):
                if not ParameterSpec.objects.filter(module_version=new_version, id_name=old_spec.id_name).exists():
                    ParameterVal.objects.get(wf_module=wfm, parameter_spec=old_spec).delete() # must exist b/c wfm exists

            wfm.module_version = new_version
            wfm.save()


