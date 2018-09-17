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
# returns module_version
def load_module_from_dict(d):

    with transaction.atomic():
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
        module.has_zen_mode = d.get('has_zen_mode', False)
        module.row_action_menu_entry_title = d.get(
            'row_action_menu_entry_title',
            ''
        )

        module.save()

        source_version = d.get('source_version', '1.0')  # if no source_version, internal module, version 1.0 always
        try:
            # if we are loading the same version again, re-use existing module_version
            module_version = ModuleVersion.objects.get(module=module, source_version_hash=source_version)
            reusing_version = True
        except ModuleVersion.DoesNotExist:
            module_version = ModuleVersion(module=module, source_version_hash=source_version)
            reusing_version = False

        module_version.html_output = d.get('html_output', False)
        module_version.save()

        # load params
        if 'parameters' in d:
            pspecs = [ load_parameter_spec(p, module_version, order) for (order,p) in enumerate(d['parameters']) ]
        else:
            pspecs = []

        # Migrate parameters, if we're updating an existing module_version
        if reusing_version:
            # Deleted parameters
            new_id_names = [p.id_name for p in pspecs]
            for old_spec in ParameterSpec.objects.filter(module_version=module_version):
                if old_spec.id_name not in new_id_names:
                    old_spec.delete() # also deletes old ParameterVals via cascade

            for new_spec in pspecs:
                try:
                    # Changed parameters
                    old_spec = ParameterSpec.objects.\
                        exclude(id=new_spec.id).\
                        get(id_name=new_spec.id_name, module_version=module_version)
                    for pv in ParameterVal.objects.filter(parameter_spec=old_spec):
                        migrate_parameter_val(pv, old_spec, new_spec)
                    old_spec.delete()

                except ParameterSpec.DoesNotExist:
                    # Added parameters
                    for wfm in WfModule.objects.filter(module_version=module_version):
                        create_parameter_val(wfm, new_spec)

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

    pspec = ParameterSpec(name=name, id_name=id_name, type=ptype, module_version=module_version)

    # Optional keys
    pspec.def_value = d.get('default', '') # ParameterVal.set_value will translate to 0, false, etc. according to type
    pspec.def_visible = d.get('visible', True)
    pspec.ui_only = d.get('ui-only', False)
    pspec.multiline = d.get('multiline', False)
    pspec.placeholder = d.get('placeholder', '')

    if d['type'] == 'menu':
        if (not 'menu_items' in d) or (d['menu_items']==''):
            raise ValueError("Menu parameter specification missing menu_items")
        pspec.def_items = d['menu_items']

    if d['type'] == 'radio':
        if (not 'radio_items' in d) or (d['radio_items']==''):
            raise ValueError("Radio parameter specification missing radio_items")
        pspec.def_items = d['radio_items']

    if 'visible_if' in d:
        if 'id_name' in d['visible_if'] and 'value' in d['visible_if']:
            pspec.visible_if = json.dumps(d.get('visible_if', {}))
        else:
            raise ValueError('visible_if must have "id_name" and "value" attributes')

    pspec.order = order
    pspec.save()

    return pspec

# --- Parameter Spec migration ----
# Handles existing ParameterVals when a module's parameters change
# This can happen when reloading an internal module (because there is only one module_version)
# or when updating a WfModule to a new module_version

def create_parameter_val(wfm, new_spec):
    pval = ParameterVal.objects.create(wf_module=wfm, parameter_spec=new_spec)
    pval.init_from_spec()
    pval.save()

# (old, new) pairs of parameter specs that _could_ be safe to maintain _if_
# dependent attributes have the same value
_safe_param_types_to_migrate = {
    (ParameterSpec.MENU, ParameterSpec.RADIO): ['def_items'],
    (ParameterSpec.RADIO, ParameterSpec.MENU): ['def_items']
}

# Checks if old parameter value can safely be maintained according to mapping in _safe_param_types_to_migrate
def _is_pval_safe_to_keep(old_spec, new_spec):
    rel = (old_spec.type, new_spec.type)
    if rel in _safe_param_types_to_migrate:
        result = [(getattr(old_spec, x) == getattr(new_spec, x)) for x in _safe_param_types_to_migrate[rel]]
        return all(result)
    return False

# Update a parameter value from one ParameterSpec to another. Resets to default if type changes.
def migrate_parameter_val(pval, old_spec, new_spec):
    type_changed = old_spec.type != new_spec.type
    pval.order = new_spec.order
    pval.parameter_spec = new_spec
    if type_changed and not _is_pval_safe_to_keep(old_spec, new_spec):
        pval.init_from_spec()
    pval.save()


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

            wfm.cache_render_result(None, None)
            wfm.module_version = new_version
            wfm.save()
