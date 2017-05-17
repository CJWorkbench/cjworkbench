# Run the workflow, on user command

import os
import json
from server.models import Workflow, Module, WfModule, ParameterVal
import pandas as pd
import numpy as np

import logging
logger = logging.getLogger(__name__)


# Return the output of a particular module. No caching yet...
def execute_wfmodule(wfmodule):
    table = pd.DataFrame()
    workflow = wfmodule.workflow
    for wfm in workflow.wf_modules.all():
        #wfm.set_ready(notify=True)          # reset errors when we re-render, as input has changed
        table = wfm.execute(table)
        if wfm == wfmodule:
            break

    if table is None:
        table = pd.DataFrame()

    return table




