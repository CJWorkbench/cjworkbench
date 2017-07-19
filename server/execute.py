# Run the workflow, generating table output

from server.models import Workflow, Module, WfModule, ParameterVal
from server.dispatch import module_dispatch_render
import pandas as pd
import numpy as np

# Return the output of a particular module. No caching yet...
def execute_wfmodule(wfmodule):
    table = pd.DataFrame()
    workflow = wfmodule.workflow
    for wfm in workflow.wf_modules.all():
        table = module_dispatch_render(wfm, table)
        if wfm == wfmodule:
            break

    if table is None:
        table = pd.DataFrame()

    return table




