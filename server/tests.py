from django.test import TestCase
from .views import workflow_list
from rest_framework.test import APIRequestFactory
from .models import ParameterVal, ParameterSpec, Module, WfModule, Workflow

class WorkflowTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_status_workflows(self):
        request = self.factory.get('/workflows/')
        response = workflow_list(request)
        self.assertIs(response.status_code, 200)

    def test_add_workflow(self):
        newParamVal = ParameterVal(numVal=3, strVal='')
        newParamVal.save()
        newParamSpec = ParameterSpec(name='test_param_spec', defaultVal=newParamVal)
        newParamSpec.save()
        newModule = Module(name='module 1')
        newModule.save()
        newModule.parameterSpecs.add(newParamSpec)
        newModule.save()
        newWfModule = WfModule(order = 1, module=newModule)
        newWfModule.save()
        newWfModule.parameters.add(newParamVal)
        newWfModule.save()
        request = self.factory.post('/api/workflows/', {'name': 'workflow 1', 'creation_date': None, 'modules': [newWfModule]})
        response = workflow_list(request)
        self.assertIs(response.status_code, 201)
        request = self.factory.get('/api/workflows/')
        response = workflow_list(request)
        content = response.render().content
        print(content)

    def test_number_workflows(self):
        request = self.factory.get('/api/workflows/')
        response = workflow_list(request)
        content = response.render().content
        print(content)