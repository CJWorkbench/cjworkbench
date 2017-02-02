from django.test import TestCase
from rest_framework import status
from server.models import Module, WfModule, Workflow, ParameterSpec, ParameterVal
from server.tests.utils import *
import pandas as pd
import io

class PasteCSVTests(TestCase):

    def setUp(self):
        self.module = add_new_module('Module 1', 'pastecsv')
        self.pspec = add_new_parameter_spec(self.module, 'csv', ParameterSpec.TEXT)
        self.workflow = add_new_workflow('Workflow 1')
        self.wfmodule = add_new_wf_module(self.workflow, self.module, 0)
        self.wfmodule.create_default_parameters()

    def test_csv(self):
        csvtext = 'Month, Amount\nJan,10\nFeb,20'

        pval = ParameterVal.objects.get(parameter_spec=self.pspec)
        pval.text = csvtext
        pval.save()

        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)
        table = pd.read_csv(io.StringIO(csvtext))
        self.assertEqual(response.content, table_to_content(table))