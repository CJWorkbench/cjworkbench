from .models.ModuleVersion import ModuleVersion

import importlib, inspect, os
import importlib.util


#the base directory where all modules imported should be stored, i.e. the place where we go to lookup
#modules that aren't pre-loaded when the workbench starts up.
_DYNAMIC_MODULES_BASE_DIRECTORY = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), '..', 'importedmodules')

#this datastructure is a dict of dicts. The key is the module name (dispatch) and the value is another
#dictionary. In this dictionary, the key is the version and the value is the render function.
_dynamic_module_dispatches = {} # {module-{version-class}}


def dynamically_load_module(wf_module):
    #load correct ModuleVersion based on the wf_module sent down by the UI, if it exists.
    #do we want to make the ModuleVersion call here directly, or hide it behind some kind of a wrapper?
    module_version =  ModuleVersion.objects.filter(module=wf_module.module_version.module,
                                    source_version_hash=wf_module.module_version.source_version_hash)
    if len(module_version) == 1:
        # Because the module is already in the database, we are making a whole bunch of assumptions here.
        # (i) the files exist
        # (ii) the module has undergone all the validation steps prior to being inserted into the database.
        # (iii) the files/scripts on disk haven't changed or been tampered with
        # (iv) all dependencies for the module have already been installed, i.e. (say the importable module
        # has a requirements.txt file, the libraries within should be part of our python path.

        # insert expected path to python path
        module_name = wf_module.module_version.module.id_name
        module_hash = wf_module.module_version.source_version_hash
        path_to_code = os.path.join(
            _DYNAMIC_MODULES_BASE_DIRECTORY, module_name, module_hash
        )

        # for now, we are working on the assumption that there's a single Python file per importable module, so
        # we can just find the single file that should be in this directory, and boom, job done.
        for f in os.listdir(path_to_code):
            if f.endswith(".py"):
                python_file = os.path.join(path_to_code, f)
                break
        else:
            raise ValueError(f'Expected .py file in {path_to_code}')

        #Now we can load the code into memory.
        spec = importlib.util.spec_from_file_location(
            f'{module_name}.{module_hash}',
            python_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        render = getattr(module, 'render')
        return render
    else:
        raise ValueError("Unable to find module {} with version {}".format(wf_module.module_version.module,
                                                                wf_module.module_version.source_version_hash))


# -- Main entrypoints --

def get_module_render_fn(wf_module):
    version_key = wf_module.module_version.module.id_name + wf_module.module_version.source_version_hash
    if version_key in _dynamic_module_dispatches.keys():
        return _dynamic_module_dispatches[version_key]
    else:
        render_fn = dynamically_load_module(wf_module)
        _dynamic_module_dispatches[version_key] = render_fn
        return render_fn


def get_module_html_path(wf_module):
    module_version = ModuleVersion.objects.filter(module=wf_module.module_version.module,
                                source_version_hash=wf_module.module_version.source_version_hash)

    path_to_file = os.path.join(_DYNAMIC_MODULES_BASE_DIRECTORY, wf_module.module_version.module.id_name,
                                    wf_module.module_version.source_version_hash)

    for f in os.listdir(path_to_file):
        if f.endswith(".html"):
            return os.path.join(path_to_file, f)

    return ''
