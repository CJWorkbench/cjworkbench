from unittest import mock

from ..dynamicdispatch import DynamicModule
import json, os, shutil, types
import pandas
import unittest


class MockWfModule:
    def __init__(self, params):
        self.params = params
        self.last_table = None

    def create_parameter_dict(self, table):
        self.last_table = table
        return self.params


class DynamicDispatchTest(unittest.TestCase):
    def setUp(self):
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

        versiondir = os.path.join(destdir, "abcdef")
        if os.path.isdir(versiondir):
            shutil.rmtree(versiondir)
        shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data", "imported"), versiondir)

        self.module = DynamicModule('imported', 'abcdef')


    def tearDown(self):
        shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "importedmodules", "imported"))


    @property
    def render(self):
        return self.module.render


    def mock_render(self, func):
        self.module.module.render = func


    def test_load_is_cached(self):
        # if we call again, should be cached
        with mock.patch('os.listdir') as mocked:
            DynamicModule('imported', 'abcdef')
            self.assertEqual(mocked.call_count, 0)


    def test_render_none(self):
        self.assertEqual(self.render(MockWfModule({}), None), None)


    def test_render_exception(self):
        self.mock_render(lambda x, y: 1 / 0) # raise exception
        table = pandas.DataFrame()
        ret = self.render(MockWfModule({}), table)
        self.assertIs(ret[0], table) # no-op
        self.assertRegexpMatches(
            ret[1],
            f'ZeroDivisionError: .* at line \\d+ of {os.path.basename(__file__)}'
        )


    def test_render_table(self):
        table = pandas.DataFrame({ 'a': [ 'b' ] })
        out = (pandas.DataFrame({ 'b': [ 'c' ] }), None)
        self.mock_render(lambda x, y: out)
        ret = self.render(MockWfModule({}), table)
        self.assertIs(ret, out)


    def test_render_error(self):
        self.mock_render(lambda x, y: (None, 'error'))
        ret = self.render(MockWfModule({}), pandas.DataFrame())
        self.assertEqual(ret[1], 'error')


    def test_render_arg_table(self):
        table = pandas.DataFrame({ 'a': [ 'b' ] })
        self.mock_render(lambda x, y: (x, None))
        ret = self.render(MockWfModule({}), table)
        self.assertIs(ret[0], table)


    def test_render_arg_params(self):
        self.mock_render(lambda x, y: (x, repr(y)))
        wf_module = MockWfModule({ 'a': 'b' })
        table = pandas.DataFrame()
        ret = self.render(wf_module, table)

        # Assert wf_module.create_parameter_dict(table) was called
        self.assertIs(wf_module.last_table, table)

        # Assert its retval was passed to module's render()
        self.assertEqual(ret[1], repr({ 'a': 'b' }))
