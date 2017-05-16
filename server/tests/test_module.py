from django.test import TestCase
from server.views import  module_list
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from server.models import Module
from server.tests.utils import *

class ModuleTests(LoggedInTestCase):
    def setUp(self):
        super(ModuleTests, self).setUp()  # log in
        self.factory = APIRequestFactory()
        self.add_new_module('Module 1')
        self.add_new_module('Module 2')
        self.add_new_module('Module 3')

    def add_new_module(self, name):
        module = Module(name=name, id_name=name+'_internal', dispatch=name+'_dispatch')
        module.save()

    def test_module_list_get(self):
        request = self.factory.get('/api/modules/')
        force_authenticate(request, user=User.objects.first())
        response = module_list(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['name'], 'Module 1')
        self.assertEqual(response.data[1]['name'], 'Module 2')
        self.assertEqual(response.data[2]['name'], 'Module 3')


