# Utilities for testing, mostly around constructing test Workflows

from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User
from server.models import Module, ModuleVersion, Workflow, WfModule, ParameterSpec, ParameterVal
from server.initmodules import load_module_from_dict
import os
import io
import json
import pandas as pd

# --- Test data ----

mock_csv_text = 'Month,Amount\nJan,10\nFeb,20'
mock_csv_table = pd.read_csv(io.StringIO(mock_csv_text))
mock_csv_text2 = 'Month,Amount,Name\nJan,10,Alicia Aliciason\nFeb,666,Fred Frederson'
mock_csv_table2 = pd.read_csv(io.StringIO(mock_csv_text2))

# ---- Logging in ----

# Derive from this to perform all tests logged in
class LoggedInTestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='username', email='user@users.com', password='password')
        user.save()
        self.client.login(username='user@users.com', password='password')
        self.user = User.objects.first()


# ---- Setting up workflows ----

def add_new_module_version(name, dispatch=''):
    module = Module.objects.create(name=name, dispatch=dispatch)
    module_version = ModuleVersion.objects.create(source_version_hash='1.0', module=module)
    return module_version

def add_new_parameter_spec(module_version, type, id_name='', order=0, def_value=''):
    return ParameterSpec.objects.create(
        module_version=module_version,
        id_name=id_name,
        type=type,
        order=order,
        def_value=def_value)

def add_new_workflow(name):
    # Workflows have to have an owner, which means we need at least one user
    if not User.objects.exists():
        User.objects.create_user(username='username', password='password')
    return Workflow.objects.create(name=name, owner=User.objects.first())

def add_new_wf_module(workflow, module_version, order=1):
    return WfModule.objects.create(workflow=workflow, module_version=module_version, order=order)

# setup a workflow with some test data loaded into a PasteCSV module
# If no data given, use standard mock data
# returns workflow
def create_testdata_workflow(csv_text=mock_csv_text):
    # Define paste CSV module from scratch
    csv_module = add_new_module_version('Module 1', 'pastecsv')
    pspec = add_new_parameter_spec(csv_module, ParameterSpec.STRING, id_name='csv')
    add_new_parameter_spec(csv_module, ParameterSpec.CHECKBOX, id_name='has_header_row', def_value='True')

    # New workflow
    workflow = add_new_workflow('Workflow 1')

    # Create new WfModule and set param to mock_csv_text
    wfmodule = add_new_wf_module(workflow, csv_module, 0)
    wfmodule.create_default_parameters()
    pval = ParameterVal.objects.get(parameter_spec=pspec)
    pval.set_value(csv_text)
    pval.save()

    return workflow


# returns the ParameterVal defined by spec with given id_name
# (error if more than one parameter with that spec)
def get_param_by_id_name(id_name):
    return ParameterVal.objects.get(parameter_spec=ParameterSpec.objects.get(id_name=id_name))

# --- set parameters ---
def set_string(pval, str):
    pval.set_value(str)
    pval.save()

def set_integer(pval, integer):
    pval.set_value(integer)
    pval.save()


# ---- Load Modules ----

# Load module spec from same place initmodules gets it, return dict
def load_module_def(filename):
    module_path = os.path.join(settings.BASE_DIR, 'config/modules')
    fullname = os.path.join(module_path, filename + '.json')
    with open(fullname) as json_data:
        d = json.load(json_data)
    return d

# Load module spec from filename, return module_version ready for use
def load_module_version(filename):
    return load_module_from_dict(load_module_def(filename))

# Given a module spec, add it to a workflow. Create new workflow if null
# Returns WfModule
def load_and_add_module(workflow, module_spec):
    if not workflow:
        workflow = add_new_workflow('Workflow 1')

    module_version = load_module_from_dict(module_spec)
    wf_module = add_new_wf_module(workflow, module_version, 1)  # 1 = order after PasteCSV from create_mock_workflow
    wf_module.create_default_parameters()

    return wf_module
