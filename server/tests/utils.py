# Utilities for testing, mostly around constructing test Workflows

from django.db import connection
from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase
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

mock_csv_path = os.path.join(settings.BASE_DIR, 'server/tests/test_data/sfpd.csv')
mock_xlsx_path = os.path.join(settings.BASE_DIR, 'server/tests/test_data/test.xlsx')


class DbTestCase(SimpleTestCase):
    allow_database_queries = True

    def tearDown(self):
        clear_db()
        super().tearDown()


# Derive from this to perform all tests logged in
class LoggedInTestCase(DbTestCase):
    def setUp(self):
        super().setUp()

        self.user = create_test_user()
        self.client.force_login(self.user)


def create_test_user(username='username', email='user@example.org',
                     password='password'):
    return User.objects.create(username=username, email=email,
                               password=password)


_Tables = [
    'server_addmodulecommand',
    'server_changedataversioncommand',
    'server_changeparametercommand',
    'server_changewfmodulenotescommand',
    'server_changewfmoduleupdatesettingscommand',
    'server_changeworkflowtitlecommand',
    'server_deletemodulecommand',
    'server_delta',
    'server_module',
    'server_moduleversion',
    'server_parameterspec',
    'server_parameterval',
    'server_reordermodulescommand',
    'server_storedobject',
    'server_uploadedfile',
    'server_wfmodule',
    'server_workflow',
    'django_session',
    'auth_group',
    'auth_group_permissions',
    'auth_permission',
    'cjworkbench_userprofile',
    'auth_user',
    'auth_user_groups',
    'auth_user_user_permissions',
]

if 'postgres' in settings.DATABASES['default']['ENGINE']:
    _clear_db_sql = f"""
    WITH f{', '.join([f't{i} AS (DELETE FROM {table})' for i, table in enumerate(_Tables)])}
    SELECT 1
    """

    def clear_db():
        with connection.cursor() as c:
            c.execute(_clear_db_sql)

else:
    def clear_db():
        with connection.cursor() as c:
            c.execute('BEGIN')
            for table in _Tables:
                c.execute(f'DELETE FROM {table}')
            c.execute('COMMIT')


# ---- Setting up workflows ----

def add_new_module_version(name, *, id_name='', dispatch=''):  # * means don't let extra arguments fill up the kwargs
    module = Module.objects.create(name=name, id_name=id_name, dispatch=dispatch)
    module_version = ModuleVersion.objects.create(source_version_hash='1.0', module=module)
    return module_version

def add_new_parameter_spec(module_version, type, id_name='', order=0, def_value=''):
    return ParameterSpec.objects.create(
        module_version=module_version,
        id_name=id_name,
        type=type,
        order=order,
        def_value=def_value)

def add_new_workflow(name, **kwargs):
    # Workflows have to have an owner, which means we need at least one user
    if 'owner' not in kwargs:
        if not User.objects.exists():
            kwargs['owner'] = User.objects.create_user(username='username', password='password')
        else:
            kwargs['owner'] = User.objects.first()
    return Workflow.objects.create(name=name, **kwargs)

def add_new_wf_module(workflow, module_version, order=0):
    wfm = WfModule.objects.create(workflow=workflow, module_version=module_version, order=order)
    wfm.create_default_parameters()
    return wfm

# setup a workflow with some test data loaded into a PasteCSV module
# If no data given, use standard mock data
# returns workflow
def create_testdata_workflow(csv_text=mock_csv_text):
    # Define paste CSV module from scratch
    csv_module = add_new_module_version('Module 1', dispatch='pastecsv')
    pspec = add_new_parameter_spec(csv_module, ParameterSpec.STRING, id_name='csv')
    add_new_parameter_spec(csv_module, ParameterSpec.CHECKBOX, id_name='has_header_row', def_value='True')

    # New workflow
    workflow = add_new_workflow('Workflow 1')

    # Create new WfModule and set param to mock_csv_text
    wfmodule = add_new_wf_module(workflow, csv_module, 0)
    pval = ParameterVal.objects.get(parameter_spec=pspec)
    pval.set_value(csv_text)
    pval.save()

    return workflow


# returns the ParameterVal defined by spec with given id_name
# optionally looks only within a specific WfModule
# Eerror if more than one ParameterVal matches
def get_param_by_id_name(id_name, wf_module=None):
    if wf_module is None:
        return ParameterVal.objects.get(parameter_spec__id_name=id_name)
    else:
        return ParameterVal.objects.get(parameter_spec__id_name=id_name, wf_module=wf_module)


# --- set parameters ---
def set_param(pval, value):
    pval.set_value(value)
    pval.save()


set_integer = set_param
set_string = set_param


# ---- Load Modules ----

# Load module spec from same place initmodules gets it, return dict
def load_module_dict(filename):
    module_path = os.path.join(settings.BASE_DIR, 'server/modules')
    fullname = os.path.join(module_path, filename + '.json')
    with open(fullname) as json_data:
        d = json.load(json_data)
    return d

# Load module spec from filename, return module_version ready for use
def load_module_version(filename):
    return load_module_from_dict(load_module_dict(filename))

# Given a module spec, add it to end of workflow. Create new workflow if null
# Returns WfModule
def load_and_add_module_from_dict(module_dict, workflow=None):
    if not workflow:
        workflow = add_new_workflow('Workflow 1')

    module_version = load_module_from_dict(module_dict)
    num_modules = WfModule.objects.filter(workflow=workflow).count()
    wf_module = add_new_wf_module(workflow, module_version, order=num_modules)

    return wf_module

# Given a module spec, add it to end of workflow. Create new workflow if null.
# Returns WfModule
def load_and_add_module(filename, workflow=None):
    return load_and_add_module_from_dict(load_module_dict(filename), workflow=workflow)
