from unittest.mock import Mock
from unittest import mock

from server.tests.utils import *
from ..dynamicdispatch import  DynamicDispatch

import json, os, shutil, sys

class DynamicDispatchTest(LoggedInTestCase):
    def setUp(self):
        super(DynamicDispatchTest, self).setUp()  # log in

    def tearDown(self):
        super(DynamicDispatchTest, self).tearDown()
        shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules/dynamic/importable"))


    #creates dummy objects of thigns we need for testing like workflow, wf_module, module_version, module, etc.
    def create_components(self):
        #extract module specification from test_data/importable
        pwd = os.path.dirname(os.path.abspath(__file__))
        test_json = os.path.join(pwd, "test_data/importable", "importable.json")
        with open(test_json) as readable:
            module_config = json.load(readable)
        wf = add_new_workflow('workflow')
        wf_module = load_and_add_module(wf, module_config)
        return wf, wf_module

    def setup_directory(self):
        #set-up structure, i.e. a way for the file to exist in a location where it can be loaded dynamically
        #copy files to where they would be if this were a real module, i.e. a non-test module.
        if not os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules/dynamic/")):
            os.makedirs(os.path.dirname(os.path.abspath(__file__)), "..", "modules/dynamic/")

        shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data", "importable"),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules/dynamic/importable", "1.0"))



    def test_load_module(self):
        dynamicdispatch = DynamicDispatch()

        wf, wf_module = self.create_components()
        self.setup_directory()

        # ensure item is loaded from file system
        dispatched = dynamicdispatch.load_module(wf_module, [1,2,3,4], dispatch=wf_module.module_version.module.name)
        self.assertEquals(type(dispatched), type, "load_module should return a class.")
        self.assertEquals(dispatched.__name__, 'Importable', 'load_module should return an instance of Importable.')

    @mock.patch.object(DynamicDispatch, 'dynamically_load_module')
    def test_load_module_cached(self, mocked):
        # ensure item is loaded from dict
        dynamicdispatch = DynamicDispatch()
        wf, wf_module = self.create_components()
        self.setup_directory()

        # first call, which should cache the module
        dispatched = dynamicdispatch.load_module(wf_module, [1, 2, 3, 4], dispatch=wf_module.module_version.module.name)
        self.assertEqual(mocked.call_count, 1, "DynamicDispatch.dynamically_load_module should've been called through load_module.")

        # second call, which should retrieve module from cache.
        dispatched = dynamicdispatch.load_module(wf_module, [1, 2, 3, 4], dispatch=wf_module.module_version.module.name)
        self.assertLess(mocked.call_count, 2,
                 "DynamicDispatch.dynamically_load_module should've only been called once.")
