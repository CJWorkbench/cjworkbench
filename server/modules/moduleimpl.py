from server.models import Module, WfModule

# ---- Module implementations ---

# Base class for all modules. Really just a reminder of function signatures
class ModuleImpl:
    @staticmethod
    def render(wfmodule, table):
        return table

    @staticmethod
    def event(wfm, **kwargs):
        pass
