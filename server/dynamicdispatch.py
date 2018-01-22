from .models.ModuleVersion import ModuleVersion

import importlib, inspect, os, sys

class DynamicDispatch:

    #the base directory where all modules imported should be stored, i.e. the place where we go to lookup
    #modules that aren't pre-loaded when the workbench starts up.
    DYNAMIC_MODULES_BASE_DIRECTORY = os.path.join(
        os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), '..', 'importedmodules'
    )

    def __init__(self):
        #this datastructure is a dict of dicts. The key is the module name (dispatch) and the value is another
        #dictionary. In this dictionary, the key is the version and the value is the class.
        self.dynamic_module_dispatches = {} # {module-{version-class}}

    def load_module(self, wf_module):
        if wf_module.module_version in self.dynamic_module_dispatches.keys():
            return self.dynamic_module_dispatches[wf_module.module_version]
        else:
            temp_class = self.dynamically_load_module(wf_module)
            self.dynamic_module_dispatches[wf_module.module_version] = temp_class
            return temp_class

    def dynamically_load_module(self, wf_module):
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
            path_to_code = os.path.join(self.DYNAMIC_MODULES_BASE_DIRECTORY, wf_module.module_version.module.id_name,
                                            wf_module.module_version.source_version_hash)
            sys.path.insert(0, path_to_code)

            # for now, we are working on the assumption that there's a single Python file per importable module, so
            # we can just find the single file that should be in this directory, and boom, job done.
            for f in os.listdir(path_to_code):
                if f.endswith(".py"):
                    python_file = os.path.join(path_to_code, f)
                    break

            #Now we can load the code into memory.
            temp = importlib.machinery.SourceFileLoader(os.path.join(path_to_code, f),
                                                        os.path.join(path_to_code, f)).load_module()
            globals().update(temp.__dict__)
            temp_class = inspect.getmembers(temp, inspect.isclass)[0][1]
            return temp_class
        else:
            raise ValueError("Unable to find module {} with version {}".format(wf_module.module_version.module,
                                                                    wf_module.module_version.source_version_hash))

    def html_output_path(self, wf_module):
        module_version = ModuleVersion.objects.filter(module=wf_module.module_version.module,
                                    source_version_hash=wf_module.module_version.source_version_hash)

        path_to_file = os.path.join(self.DYNAMIC_MODULES_BASE_DIRECTORY, wf_module.module_version.module.id_name,
                                        wf_module.module_version.source_version_hash)

        for f in os.listdir(path_to_file):
            if f.endswith(".html"):
                return os.path.join(path_to_file, f)

        return ''
