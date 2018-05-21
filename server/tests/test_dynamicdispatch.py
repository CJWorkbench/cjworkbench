from unittest import mock

from server.tests.utils import *
from ..dynamicdispatch import get_module_render_fn
import json, os, shutil, types

class DynamicDispatchTest(LoggedInTestCase):
    def setUp(self):
        super(DynamicDispatchTest, self).setUp()  # log in

    def tearDown(self):
        super(DynamicDispatchTest, self).tearDown()
        shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "importedmodules", "imported"))


    #creates dummy objects of things we need for testing like workflow, wf_module, module_version, module, etc.
    def create_components(self):
        # Extract module specification from test_data/imported.
        # This has the modified .py file that add_boilerplate_and_check_syntax() creates when it loads from github
        pwd = os.path.dirname(os.path.abspath(__file__))
        test_json = os.path.join(pwd, "test_data/imported", "imported.json")
        with open(test_json) as readable:
            module_config = json.load(readable)
        wf = add_new_workflow('workflow')
        wf_module = load_and_add_module_from_dict(module_config, workflow=wf)
        return wf, wf_module

    def setup_directory(self):
        #set-up structure, i.e. a way for the file to exist in a location where it can be loaded dynamically
        #copy files to where they would be if this were a real module, i.e. a non-test module.
        destdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "importedmodules", "imported")
        if not os.path.isdir(destdir):
            os.makedirs(destdir)

        versiondir = os.path.join(destdir, "1.0")
        if os.path.isdir(versiondir):
            shutil.rmtree(versiondir)
        shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data", "imported"), versiondir)


    def test_load_module(self):
        wf, wf_module = self.create_components()
        self.setup_directory()

        render_fn = get_module_render_fn(wf_module)
        self.assertTrue(isinstance(render_fn, types.FunctionType))

        # if we call again, should be cached
        with mock.patch('server.dynamicdispatch.dynamically_load_module') as mocked:
            get_module_render_fn(wf_module)
            self.assertEqual(mocked.call_count, 0)
