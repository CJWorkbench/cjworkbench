# Run the workflow, on user command

import os
import json
from server.models import Workflow, Module, WfModule, ParameterVal

import pandas as pd
import numpy as np

import logging
logger = logging.getLogger(__name__)

# Basic execution path: run each workflow in sequence, transforming the input table
def execute_workflow(workflow):
    table = None
    for wf_module in workflow.wf_modules.all():
        table = wf_module.execute(table)

    print(table)

# Return the output of a particular module. No caching yet...
def execute_wfmodule(wfmodule):
    table = None
    workflow = wfmodule.workflow
    for wfm in workflow.wf_modules.all():
        table = wfm.execute(table)

        if wfm == wfmodule:
            break

    return table




