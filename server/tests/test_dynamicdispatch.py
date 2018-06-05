from unittest import mock

from server.tests.utils import LoggedInTestCase, load_and_add_module_from_dict, add_new_workflow
from ..dynamicdispatch import get_module_render_fn, wf_module_to_dynamic_module
import json, os, shutil, types
import pandas

class DynamicDispatchTest(LoggedInTestCase):
    def setUp(self):
        super(DynamicDispatchTest, self).setUp()  # log in

    def tearDown(self):
        super(DynamicDispatchTest, self).tearDown()
        shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "importedmodules", "imported"))


    @property
    def a_workflow(self):
        if hasattr(self, '_workflow'): return self._workflow

        self._workflow = add_new_workflow('workflow')
        return self._workflow


    @property
    def a_wf_module(self):
        if hasattr(self, '_wf_module'): return self._wf_module

        # Extract module specification from test_data/imported.
        # This has the modified .py file that add_boilerplate_and_check_syntax() creates when it loads from github
        pwd = os.path.dirname(os.path.abspath(__file__))
        test_json = os.path.join(pwd, "test_data/imported", "imported.json")
        with open(test_json) as readable:
            module_config = json.load(readable)

        #set-up structure, i.e. a way for the file to exist in a location where it can be loaded dynamically
        #copy files to where they would be if this were a real module, i.e. a non-test module.
        destdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "importedmodules", "imported")
        if not os.path.isdir(destdir):
            os.makedirs(destdir)

        versiondir = os.path.join(destdir, "1.0")
        if os.path.isdir(versiondir):
            shutil.rmtree(versiondir)
        shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data", "imported"), versiondir)

        self._wf_module = load_and_add_module_from_dict(module_config,
                                                        workflow=self.a_workflow)
        return self._wf_module


    @property
    def a_dynamic_module(self):
        if hasattr(self, '_dynamic_module'): return self._dynamic_module

        self._dynamic_module = wf_module_to_dynamic_module(self.a_wf_module)
        return self._dynamic_module


    @property
    def render(self):
        return self.a_dynamic_module.render


    def mock_render(self, func):
        self.a_dynamic_module.module.render = func


    def test_load_module(self):
        render_fn = get_module_render_fn(self.a_wf_module)
        self.assertTrue(callable(render_fn))


    def test_load_module_is_cached(self):
        get_module_render_fn(self.a_wf_module)
        # if we call again, should be cached
        with mock.patch('os.listdir') as mocked:
            get_module_render_fn(self.a_wf_module)
            self.assertEqual(mocked.call_count, 0)


    def test_render_none(self):
        self.assertEqual(self.render(None, {}), None)


    def test_render_exception(self):
        self.mock_render(lambda x, y: 1 / 0) # raise exception
        table = pandas.DataFrame()
        ret = self.render(table, {})
        self.assertIs(ret[0], table) # no-op
        self.assertRegexpMatches(
            ret[1],
            f'ZeroDivisionError: .* at line \\d+ of {os.path.basename(__file__)}'
        )


    def test_render_table(self):
        table = pandas.DataFrame({ 'a': [ 'b' ] })
        out = (pandas.DataFrame({ 'b': [ 'c' ] }), None)
        self.mock_render(lambda x, y: out)
        ret = self.render(table, {})
        self.assertIs(ret, out)


    def test_render_error(self):
        self.mock_render(lambda x, y: (None, 'error'))
        ret = self.render(pandas.DataFrame(), {})
        self.assertEqual(ret[1], 'error')


    def test_render_arg_table(self):
        table = pandas.DataFrame({ 'a': [ 'b' ] })
        self.mock_render(lambda x, y: (x, None))
        ret = self.render(table, {})
        self.assertIs(ret[0], table)


    def test_render_arg_params(self):
        self.mock_render(lambda x, y: (x, repr(y)))
        ret = self.render(pandas.DataFrame(), { 'a': 'b' })
        self.assertEqual(ret[1], repr({ 'a': 'b' }))
