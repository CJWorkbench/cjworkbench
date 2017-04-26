# Utilities for testing, mostly around constructing test Workflows

from django.test import TestCase
from server.models import Module, Workflow, WfModule, ParameterSpec
from django.contrib.auth.models import User

def add_new_module(name, dispatch=''):
    return Module.objects.create(name=name, dispatch=dispatch)

def add_new_parameter_spec(module, id_name, type, order=0):
    return ParameterSpec.objects.create(module=module, id_name=id_name, type=type, order=order)

def add_new_workflow(name):
    return Workflow.objects.create(name=name, owner=User.objects.first())

def add_new_wf_module(workflow, module, order=1):
    return WfModule.objects.create(workflow=workflow, module=module, order=order)

# Encodes a DataFrame to the expected response format form render API
def table_to_content(table):
    return table.to_json(orient='records').encode('UTF=8')

# Derive from this to perform all tests logged in
class LoggedInTestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='username', password='password')
        user.save()
        self.client.login(username='username', password='password')
        self.user = User.objects.first()