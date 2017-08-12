from django.test import TestCase
import json
from server.views.WfModule import wfmodule_detail, wfmodule_render, wfmodule_dataversion
from rest_framework.test import APIRequestFactory
from rest_framework import status
from server.models import Module, ModuleVersion, WfModule, Workflow, ParameterSpec, ParameterVal
from server.dispatch import test_data_table
from server.tests.utils import *
from rest_framework.test import force_authenticate

class WfModuleTests(LoggedInTestCase):

    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super(WfModuleTests, self).setUp()  # log in
        self.factory = APIRequestFactory()
        self.workflow1 = add_new_workflow(name='Workflow 1')
        self.workflow2 = add_new_workflow(name='Workflow 2')

        self.module1_version = self.add_new_module_version(name='Module 1', dispatch='testdata', version="1.0")
        self.pspec11 = ParameterSpec.objects.create(module_version=self.module1_version, type=ParameterSpec.FLOAT, def_value=3.14, def_visible=False)
        self.pspec12 = ParameterSpec.objects.create(module_version=self.module1_version, type=ParameterSpec.STRING, def_value='foo')
        self.pspec13 = ParameterSpec.objects.create(module_version=self.module1_version, type=ParameterSpec.CHECKBOX, def_value='True')

        self.module2_version = self.add_new_module_version(name='Module 2', dispatch='NOP', version="1.0")
        self.pspec21 = ParameterSpec.objects.create(module_version=self.module2_version, type=ParameterSpec.MENU, def_menu_items='Apple|Banana|Kittens', def_value='1')

        self.module3_version = self.add_new_module_version(name='Module 3', dispatch='double_M_col', version="1.0")
        self.pspec31 = ParameterSpec.objects.create(module_version=self.module3_version, type=ParameterSpec.BUTTON)

        self.wfmodule1 = self.add_new_wfmodule(self.workflow1, self.module1_version, 1)
        self.wfmodule2 = self.add_new_wfmodule(self.workflow1, self.module2_version, 2)
        self.wfmodule3 = self.add_new_wfmodule(self.workflow1, self.module3_version, 3)
        self.add_new_wfmodule(self.workflow2, self.module1_version, 1)
        self.add_new_wfmodule(self.workflow2, self.module2_version, 2)
        self.add_new_wfmodule(self.workflow2, self.module3_version, 3)


    # --- utils ---

    def add_new_wfmodule(self, workflow_aux, module_aux, order_aux):
        return WfModule.objects.create(workflow=workflow_aux, module_version=module_aux, order=order_aux)

    def add_new_module(self, name, dispatch):
        return Module.objects.create(name=name, dispatch=dispatch)

    def add_new_module_version(self, name, dispatch, version):
        module = self.add_new_module(name=name, dispatch=dispatch)
        module.save()
        module_version = ModuleVersion.objects.create(module = module, source_version_hash = version)
        module_version.save()
        return module_version


    # --- tests ---

    # check that creating a wf_module correctly sets up new ParameterVals w/ defaults from ParameterSpec
    def test_default_parameters(self):
        self.wfmodule1.create_default_parameters()
        pval = ParameterVal.objects.get(parameter_spec=self.pspec11, wf_module=self.wfmodule1)
        self.assertEqual(pval.value, '3.14')
        self.assertEqual(pval.visible, False)

        pval = ParameterVal.objects.get(parameter_spec=self.pspec12, wf_module=self.wfmodule1)
        self.assertEqual(pval.value, 'foo')
        self.assertEqual(pval.visible, True)

        pval = ParameterVal.objects.get(parameter_spec=self.pspec13, wf_module=self.wfmodule1)
        self.assertEqual(pval.value, '1')
        self.assertEqual(pval.visible, True)

        # Menu should have correct default item
        self.wfmodule2.create_default_parameters()
        pval = ParameterVal.objects.get(parameter_spec=self.pspec21, wf_module=self.wfmodule2)
        self.assertEqual(pval.selected_menu_item_string(), 'Banana')

        # button has no value, so just checking existence here
        self.wfmodule3.create_default_parameters()
        pval = ParameterVal.objects.get(parameter_spec=self.pspec31, wf_module=self.wfmodule3)
        self.assertEqual(pval.visible, True)

    # TODO test parameter values returned from this call
    def test_wf_module_detail_get(self):
        # Also tests [Workflow, Module, WfModule].get
        workflow_id = Workflow.objects.get(name='Workflow 1').id
        module_id = Module.objects.get(name='Module 1').id
        module_version = ModuleVersion.objects.get(module = Module.objects.get(name='Module 1'))
        pk_wf_module = WfModule.objects.get(workflow_id=workflow_id,
                                           module_version = module_version).id
        notes = WfModule.objects.get(workflow_id=workflow_id,
                                           module_version = module_version).notes

        response = self.client.get('/api/wfmodules/%d/' % pk_wf_module)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], pk_wf_module)
        self.assertEqual(response.data['workflow'], workflow_id)
        self.assertEqual(response.data['notes'], notes)        
        self.assertEqual(response.data['module_version']['module']['id'], module_id)
        self.assertEqual(response.data['status'], WfModule.READY)
        self.assertEqual(response.data['error_msg'], '')

        response = self.client.get('/api/wfmodules/%d/' % 10000)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)



    def test_wf_module_render_get(self):
        # First module: creates test data
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = table_to_content(test_data_table)
        self.assertEqual(response.content, test_data_json)

        # second module: NOP
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, test_data_json)

        # Third module: doubles M column
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule3.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        double_test_data = pd.DataFrame(test_data_table['Class'], test_data_table['M']*2, test_data_table['F'])
        double_test_data = table_to_content(double_test_data)
        self.assertEqual(response.content, double_test_data)


    # can we take one out?
    def test_wf_module_delete(self):
        # add a new one to delete; don't mess with other tests
        wfmodule4 = self.add_new_wfmodule(self.workflow1, self.module1_version, 4)

        response = self.client.delete('/api/wfmodules/%d' % wfmodule4.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(WfModule.DoesNotExist):
            WfModule.objects.get(pk=wfmodule4.id, workflow=self.workflow1)  # must really be gone


    # /input is just a /render on the previous module
    def test_wf_module_input(self):
        # First module: no prior input, should be empty result
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = table_to_content(pd.DataFrame())
        self.assertEqual(response.content, test_data_json)

        # Second module: input should be test data produced by first module
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = table_to_content(test_data_table)
        self.assertEqual(response.content, test_data_json)

        # Third module: should be same as second, as second module is NOP
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule3.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, test_data_json)


    # test stored versions of data: create, retrieve, set, list, and views
    def test_wf_module_data_versions(self):
        text1 = 'just pretend this is json'
        text2 = 'and this is a later version'

        # nothing ever stored
        nothing = self.wfmodule1.retrieve_data()
        self.assertIsNone(nothing)

        # save and recover data
        ver1 = self.wfmodule1.store_data(text1)
        self.wfmodule1.set_stored_data_version(ver1)
        self.wfmodule1.save()
        self.wfmodule1.refresh_from_db()
        textout = self.wfmodule1.retrieve_data()
        self.assertEqual(textout, text1)
        firstver = self.wfmodule1.get_stored_data_version()

        # create another version
        secondver = self.wfmodule1.store_data(text2)
        self.wfmodule1.set_stored_data_version(secondver)
        self.assertNotEqual(firstver, secondver)
        textout = self.wfmodule1.retrieve_data()
        self.assertEqual(textout, text2)

        # change the version back
        self.wfmodule1.set_stored_data_version(firstver)
        textout = self.wfmodule1.retrieve_data()
        self.assertEqual(textout, text1)

        # invalid version string should error
        with self.assertRaises(ValueError):
            self.wfmodule1.set_stored_data_version('foo')

        # list versions
        verlist = self.wfmodule1.list_stored_data_versions()
        self.assertListEqual(verlist, [firstver, secondver])  # sorted by creation date, ascending

        # but like, none of this should have created versions on any other wfmodule
        self.assertEqual(self.wfmodule2.list_stored_data_versions(), [])

        # retrieve version list through the API
        response = self.client.get('/api/wfmodules/%d/dataversion' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        versiondata = {
            "versions": [
                firstver,
                secondver
            ],
            "selected": firstver
        }
        responsedata = json.loads(response.content.decode('UTF-8'))
        self.assertEqual(responsedata, versiondata)

        # set the version back to latest through API.
        # using factory.patch as trouble getting client.patch to work (400 -- authentication?)
        # More or less the same thing, but does skip urls.py
        request = self.factory.patch('/api/wfmodules/%d/dataversion' % self.wfmodule1.id,
                                     {'selected': secondver})
        force_authenticate(request, user=self.user)
        response = wfmodule_dataversion(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.wfmodule1.refresh_from_db()
        self.assertEqual(self.wfmodule1.get_stored_data_version(), secondver)


    # test Wf Module Notes change API
    def test_wf_module_notes_post(self):
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                   {'notes': 'wow such doge'})
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # see that we get the new value back
        response = self.client.get('/api/wfmodules/%d/' % self.wfmodule1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'wow such doge')

        # Test for error on missing notes field (and no other patachable fields)
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                     {'notnotes': 'forthcoming error'})
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    # Test set/get update interval
    def test_wf_module_update_settings(self):
        settings = {'auto_update_data' : True,
                    'update_interval'  : 5,
                    'update_units'     : 'weeks' }

        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id, settings )
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new values back
        response = self.client.get('/api/wfmodules/%d/' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['auto_update_data'], True)
        self.assertEqual(response.data['update_interval'], 5)
        self.assertEqual(response.data['update_units'], 'weeks')

        # Now check for error checking! As usual, this is most of the work
        missing_units_key = { 'auto_update_data' : True, 'update_interval': 1000 }
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id, missing_units_key)
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

        missing_interval_key = { 'auto_update_data': True, 'update_units': 'days' }
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id, missing_interval_key)
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

        bad_units_key = { 'auto_update_data': True, 'update_interval':66, 'update_units': 'pajama' }
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id, bad_units_key)
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
