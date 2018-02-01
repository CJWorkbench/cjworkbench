from django.test import TestCase
from server.views import  module_list
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from server.models import Module
from server.tests.utils import *
from cjworkbench.settings import KB_ROOT_URL

class ModuleTests(LoggedInTestCase):
    def setUp(self):
        super(ModuleTests, self).setUp()  # log in
        self.factory = APIRequestFactory()
        self.add_new_module('Module 1', help_url='category/help')
        self.add_new_module('Module 2', help_url='https://help.you')
        self.add_new_module('Module 3')

    def add_new_module(self, name, help_url=''):
        module = Module(name=name, id_name=name+'_internal', dispatch=name+'_dispatch', help_url=help_url)
        module.save()

    def test_module_list_get(self):
        request = self.factory.get('/api/modules/')
        force_authenticate(request, user=User.objects.first())
        response = module_list(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['name'], 'Module 1')
        self.assertEqual(response.data[0]['id_name'], 'Module 1_internal')
        self.assertEqual(response.data[0]['help_url'], '%scategory/help' % KB_ROOT_URL)

        self.assertEqual(response.data[1]['name'], 'Module 2')
        self.assertEqual(response.data[1]['id_name'], 'Module 2_internal')
        self.assertEqual(response.data[1]['help_url'], 'https://help.you')

        self.assertEqual(response.data[2]['name'], 'Module 3')
        self.assertEqual(response.data[2]['id_name'], 'Module 3_internal')
        self.assertEqual(response.data[2]['help_url'], KB_ROOT_URL)


