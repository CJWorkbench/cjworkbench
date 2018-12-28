import asyncio
from concurrent.futures import ThreadPoolExecutor
from django.db import connection, connections
from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase
from server import minio
from server.models import Module, ModuleVersion, Workflow, ParameterSpec
from server.models.commands import InitWorkflowCommand
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

    def setUp(self):
        clear_db()
        clear_minio()

    # Don't bother clearing data in tearDown(). The next test that needs the
    # database will be running setUp() anyway, so extra clearing will only cost
    # time.

    def run_with_async_db(self, task):
        """
        Like async_to_sync() but it closes the database connection.

        This is a rather expensive call: it connects and disconnects from the
        database.

        See
        https://github.com/django/channels/issues/1091#issuecomment-436067763.
        """
        # We'll execute with a 1-worker thread pool. That's because Django
        # database methods will spin up new connections and never close them.
        # (@database_sync_to_async -- which execute uses --only closes _old_
        # connections, not valid ones.)
        #
        # This hack is just for unit tests: we need to close all connections
        # before the test ends, so we can delete the entire database when tests
        # finish. We'll schedule the "close-connection" operation on the same
        # thread as @database_sync_to_async's blocking code ran on. That way,
        # it'll close the connection @database_sync_to_async was using.
        old_loop = asyncio.get_event_loop()

        loop = asyncio.new_event_loop()
        loop.set_default_executor(ThreadPoolExecutor(1))
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(task)
        finally:
            def close_thread_connection():
                # Close the connection that was created by
                # @database_sync_to_async.  Assumes we're running in the same
                # thread that ran the database stuff.
                connections.close_all()

            loop.run_until_complete(
                loop.run_in_executor(None, close_thread_connection)
            )

            asyncio.set_event_loop(old_loop)


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
    'server_aclentry',
    'server_addmodulecommand',
    'server_addtabcommand',
    'server_changedataversioncommand',
    'server_changeparameterscommand',
    'server_changewfmodulenotescommand',
    'server_changewfmoduleupdatesettingscommand',
    'server_changeworkflowtitlecommand',
    'server_deletemodulecommand',
    'server_deletetabcommand',
    'server_reordermodulescommand',
    'server_reordertabscommand',
    'server_settabnamecommand',
    'server_initworkflowcommand',
    'server_delta',
    'server_module',
    'server_moduleversion',
    'server_parameterspec',
    'server_parameterval',
    'server_storedobject',
    'server_uploadedfile',
    'server_wfmodule',
    'server_tab',
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


def clear_db():
    deletes = [f't{i} AS (DELETE FROM {table})'
               for i, table in enumerate(_Tables)]
    sql = f"WITH {', '.join(deletes)} SELECT 1"
    with connection.cursor() as c:
        c.execute(sql)


def clear_minio():
    minio.ensure_bucket_exists(minio.UserFilesBucket)
    minio.ensure_bucket_exists(minio.StoredObjectsBucket)

    user_files = [o.object_name
                  for o in
                  minio.minio_client.list_objects_v2(minio.UserFilesBucket,
                                                     recursive=True)]
    minio.minio_client.remove_objects(minio.UserFilesBucket, user_files)

    stored_objects = [o.object_name
                  for o in
                  minio.minio_client.list_objects_v2(minio.UserFilesBucket,
                                                     recursive=True)]
    minio.minio_client.remove_objects(minio.StoredObjectsBucket,
                                      stored_objects)


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


def add_new_workflow(name, *, owner=None, **kwargs):
    # Workflows have to have an owner, which means we need at least one user
    if 'owner' not in kwargs:
        if not User.objects.exists():
            kwargs['owner'] = User.objects.create_user(username='username', password='password')
        else:
            kwargs['owner'] = User.objects.first()
    workflow = Workflow.objects.create(name=name, **kwargs)
    workflow.tabs.create(position=0)
    InitWorkflowCommand.create(workflow)
    return workflow


def add_new_wf_module(workflow, module_version, order=0,
                      param_values={}, last_relevant_delta_id=0):
    return workflow.tabs.first().wf_modules.create(
        module_version=module_version,
        order=order,
        last_relevant_delta_id=last_relevant_delta_id,
        params={
            **module_version.get_default_params(),
            **param_values,
        }

    )

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
    wfmodule.params = {'csv': csv_text}
    wfmodule.save(update_fields=['params'])

    return workflow


# --- set parameters ---
def set_param(pval, value):
    pval.set_value(value)
    pval.save()


set_integer = set_param
set_string = set_param
set_checkbox = set_param


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
def load_and_add_module_from_dict(module_dict, workflow=None, param_values={},
                                  last_relevant_delta_id=0):
    if not workflow:
        workflow = add_new_workflow('Workflow 1')

    module_version = load_module_from_dict(module_dict)
    num_modules = workflow.tabs.first().live_wf_modules.count()
    wf_module = add_new_wf_module(workflow, module_version,
                                  param_values=param_values,
                                  last_relevant_delta_id=last_relevant_delta_id,
                                  order=num_modules)

    return wf_module

# Given a module spec, add it to end of workflow. Create new workflow if null.
# Returns WfModule
def load_and_add_module(filename, workflow=None, param_values={},
                        last_relevant_delta_id=0):
    return load_and_add_module_from_dict(
        load_module_dict(filename),
        workflow=workflow,
        param_values=param_values,
        last_relevant_delta_id=last_relevant_delta_id
    )
