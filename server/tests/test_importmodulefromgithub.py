from server.importmodulefromgithub import *
from server.dispatch import module_dispatch_render
from server.tests.utils import *
from pathlib import Path
import pandas as pd
import io, types
import mock
import logging, os, shutil

# Patch get_already_imported from importmodulefromgithub
def overriden_get_already_imported():
    return {
        "accio": "www.github.com/something",
        "lumos": ""
    }

class ImportFromGitHubTest(LoggedInTestCase):
    def setUp(self):
        super(ImportFromGitHubTest, self).setUp()  # log in

        self.importable_repo_name = 'importable'
        self.importable_id_name ='importable_not_repo_name'  # must match importable.json test data file

        self.cleanup()

        #  several tests are supposed to log an exception, but don't print that every test
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        super(ImportFromGitHubTest, self).tearDown()
        self.cleanup()

    def cleanup(self):
        # remove any directories we may have created during the last test
        clonedir = self.clone_dir()
        if os.path.isdir(clonedir):
            shutil.rmtree(clonedir)
        importdir = self.imported_dir()
        if os.path.isdir(importdir):
            shutil.rmtree(importdir)

    # Where do we initially "clone" (fake clone) github files to?
    def clone_dir(self):
        pwd = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(pwd, 'importedmodules-test')

    # Where do we install the files?
    # Actual final location has version number added to the end of this, e.g. imported_dir() + "/123456"
    def imported_dir(self):
        pwd = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(pwd, '..', '..', 'importedmodules', self.importable_id_name)


    # fills clone_dir() with a set of module files in "freshly cloned from github" state
    # erases anything previously there
    def fake_github_clone(self, source_dir='test_data/importable'):
        clonedir = self.clone_dir()
        if os.path.isdir(clonedir):
            shutil.rmtree(clonedir)
        pwd = os.path.dirname(os.path.abspath(__file__))
        shutil.copytree(os.path.join(pwd, source_dir), clonedir)
        return clonedir


    # -- Tests ---

    def test_sanitise_url(self):
        #test valid url
        input_url = "https://github.com/anothercookiecrumbles/somerepo"
        returned_url = sanitise_url(input_url)
        self.assertEqual(input_url, returned_url, "In this case, the input url doesn't need to be cleaned. Therefore " +
                         " the output {} should be the input {}.".format(returned_url, input_url))

        #test valid url with a git suffix
        input_url_git = "https://github.com/anothercookiecrumbles/somerepo.git"
        returned_url_git = sanitise_url(input_url_git)
        self.assertEqual(input_url_git, returned_url_git, ".git is optional, and we leave it")

        #test valid url with padding (i.e. extra spaces)
        input_url_spaces = "     https://github.com/anothercookiecrumbles/somerepo"
        returned_url_spaces = sanitise_url(input_url)
        self.assertEqual(input_url, returned_url_spaces, "In this case, the input url just needs to be trimmed."
                "Therefore the output {} should be the trimmed input {}.".format(returned_url, input_url_spaces))

        input_url_spaces = "     https://github.com/anothercookiecrumbles/somerepo     "
        returned_url_spaces = sanitise_url(input_url)
        self.assertEqual(input_url, returned_url_spaces, "In this case, the input url needs to be trimmed. "
                    "Therefore the output {} should be the input trimmed {}.".format(returned_url, input_url_spaces))

        #test empty string
        input_url = ""
        with self.assertRaisesMessage(ValidationError, 'Empty URL'):
            sanitise_url(input_url)

        input_url = "    " #non-trimmed empty string
        with self.assertRaisesMessage(ValidationError, 'Empty URL'):
            sanitise_url(input_url)

        #test non-url
        input_url = "this is not a url"
        with self.assertRaisesMessage(ValidationError, 'Invalid Git repo URL entered: %s' % (input_url)):
            sanitise_url(input_url)


    def test_retrieve_project_name(self):
        #Here, we assume that we have a _clean_/_sanitised_ URL; if we didn't, the code should've thrown an exception
        #earlier in the stack. Hence, we don't test _bad_ urls.

        #retrieve project name for a GitHub url, but one that doesn't end .git.
        git_url = "https://github.com/anothercookiecrumbles/somerepo"
        project_name = retrieve_project_name(git_url)
        self.assertEqual(project_name, "somerepo")


    def test_validate_module_structure(self):
        # We don't want to rely on a remote repo existing, so we drive this test off a local repo equivalent
        test_dir = self.fake_github_clone()

        mapping = validate_module_structure(test_dir)
        self.assertTrue(len(mapping) == 2, "We should only have two files in the module structure: one Python " +
                        "and one JSON.")
        self.assertTrue("json" in mapping, "A json file must exist in the module structure.")
        self.assertTrue("py" in mapping, "A python file must exist in the module structure.")
        self.assertTrue(mapping["py"] == "importable.py", "The py mapping in the module must be against the only " +
                                                        "Python file in the directory: importable.py.")
        self.assertTrue(mapping["json"] == "importable.json", "The json mapping in the module must be against the only JSON" +
                        " file in the directory: importable.json")


        # Test invalid modules: 1/ ensure only one Python and one JSON file exist.
        # Add additional JSON file to directory.
        self.fake_github_clone()
        more_json = os.path.join(test_dir, 'disposable.json')
        open(more_json, 'a').close()
        # ensure that disposable.json is created – we need this for the tests to run properly.
        self.assertTrue(os.path.isfile(more_json),
                        "disposable.json must be created in order for these unit tests to run properly.")

        with self.assertRaisesMessage(ValidationError, "Multiple files exist with extension json. This isn't currently"+
                                                       " supported"):
            mapping = validate_module_structure(test_dir)


        # Add additional Python file directory, assert this fails
        self.fake_github_clone()
        open(os.path.join(test_dir, 'disposable.py'), 'a').close()
        # ensure that disposable.py is created – we need this for the tests to run properly.
        self.assertTrue(os.path.isfile(os.path.join(test_dir, 'disposable.py')),
                        "disposable.py must be created in order for these unit tests to run properly.")

        with self.assertRaises(ValidationError):
            mapping = validate_module_structure(test_dir)

        # Test invalid modules: 2/ ensure that at least one Python and one JSON file exist.
        self.fake_github_clone()
        os.remove(os.path.join(test_dir, 'importable.json'))
        with self.assertRaises(ValidationError):
            mapping = validate_module_structure(test_dir)

        self.fake_github_clone()
        os.remove(os.path.join(test_dir, 'importable.py'))
        with self.assertRaises(ValidationError):
            mapping = validate_module_structure(test_dir)


    def test_extract_version_hash(self):
        test_dir = self.fake_github_clone()
        os.rename(os.path.join(test_dir, 'git'),
                  os.path.join(test_dir, '.git'))
        self.assertTrue(os.path.isdir(os.path.join(test_dir, ".git")))
        version = extract_version(test_dir)
        self.assertEquals(version, '7832830',
                          "The hash of the git repo should be {}, but the function returned {}.".format('427847c',
                                                                                                        version))


    @mock.patch('server.importmodulefromgithub.get_already_imported_module_urls', side_effect=overriden_get_already_imported)
    def test_validate_json(self, get_already_imported_function):
        test_dir = self.fake_github_clone()

        #ensure we get a ValidationError if the mapping doesn't have a json key, i.e. missing json file.
        mapping = {}
        with self.assertRaises(ValidationError):
            get_module_config_from_json("", mapping, test_dir)

        #check valid scenario, i.e. the system successfully parses the JSON configuration.
        mapping = {'json': 'importable.json', 'py': 'importable.py'}
        module_config = get_module_config_from_json("", mapping, test_dir)
        self.assertTrue(len(module_config) == 5, 'The configuration should have loaded 5 items, but it loaded ' +
                                                 ' {} items.'.format(len(module_config)))
        self.assertTrue(all (k in module_config for k in ("id_name", "description", "name", "category", "parameters")),
                        "Not all mandatory keys exist in the module_config/json file.")


    def test_create_destination_directory(self):
        pwd = os.path.dirname(os.path.abspath(__file__))

        # Should create destination and originals files directory
        destination_directory = create_destination_directory('my_id_name', '123456')
        expected_path = os.path.normpath(pwd + '/../../importedmodules/my_id_name/123456')
        self.assertTrue(Path(destination_directory) == Path(expected_path))
        self.assertTrue(os.path.isdir(destination_directory))
        self.assertTrue(os.path.isdir(destination_directory + '-original'))

        # should work even if files already exists for the given module-version combination
        # in which case the dir should be deleted, so as to be ready for re-import
        junkfile = os.path.join(destination_directory, "junk")
        open(junkfile, 'w+')
        self.assertTrue(os.path.isfile(junkfile))
        create_destination_directory('my_id_name','123456')
        self.assertFalse(os.path.isfile(junkfile))


    def test_add_boilerplate_and_check_syntax(self):
        test_dir = self.fake_github_clone()
        destination_directory = os.path.join(self.imported_dir(), "123456")

        os.makedirs(destination_directory)
        shutil.copy(os.path.join(test_dir, "importable.py"), destination_directory)

        # test valid scenario. Failures should raise ValidationError
        compiled = add_boilerplate_and_check_syntax(destination_directory, "importable.py")
        shutil.rmtree(destination_directory)

        # test invalid scenario: what if Python file doesn't exist.
        self.fake_github_clone()
        os.makedirs(destination_directory)
        with self.assertRaises(ValidationError):
            compiled = add_boilerplate_and_check_syntax(destination_directory, "importable.py")

        # test invalid scenario: what if Python file exists but can't be compiled.
        # create file and add some random content to file
        f = open(os.path.join(test_dir, 'additional_file.py'), 'a')
        f.write("random content here")
        f.close()
        shutil.copy(os.path.join(test_dir, "additional_file.py"), destination_directory)

        with self.assertRaises(ValidationError):
            compiled = add_boilerplate_and_check_syntax(destination_directory, "additional_file.py")


    def test_validate_python_functions(self):

        #test valid scenario
        test_dir = self.fake_github_clone()
        add_boilerplate_and_check_syntax(test_dir , "importable.py")  # adds crucial boilerplate to the file
        render_fn = validate_python_functions(test_dir , "importable.py")
        self.assertTrue(isinstance(render_fn, types.FunctionType), "The module must be importable, and be of type 'type'.")

        # test missing/unloadable render function
        test_dir = self.fake_github_clone('test_data/missing_render_module')
        add_boilerplate_and_check_syntax(test_dir, "missing_render_module.py")
        with self.assertRaises(ValidationError):
            validate_python_functions(test_dir, "missing_render_module.py")


    # syntax errors in module source files should be detected
    def test_load_invalid_code(self):
        test_dir = self.fake_github_clone('test_data/bad_json_module')
        with self.assertRaises(ValidationError):
            import_module_from_directory("https://test_url_of_test_module", "bad_json_module", "123456", test_dir)

        test_dir = self.fake_github_clone('test_data/bad_py_module')
        with self.assertRaises(ValidationError):
            import_module_from_directory("https://test_url_of_test_module", "bad_py_module", "123456", test_dir)


    # loading the same version of the same module twice should fail
    def test_load_twice(self):
        test_dir = self.fake_github_clone()
        import_module_from_directory("https://test_url_of_test_module", "importable", "123456", test_dir)

        test_dir = self.fake_github_clone() # import moves files, so get same files again
        with self.assertRaises(ValidationError):
            import_module_from_directory("https://test_url_of_test_module", "importable", "123456", test_dir)


    # We will do a reload of same version if force_reload==True
    def test_load_twice_force_relaod(self):
        test_dir = self.fake_github_clone()
        import_module_from_directory("https://test_url_of_test_module", "importable", "123456", test_dir)
        self.assertEqual(ModuleVersion.objects.filter(module__id_name=self.importable_id_name).count(), 1)

        test_dir = self.fake_github_clone() # import moves files, so get same files again
        import_module_from_directory("https://test_url_of_test_module", "importable", "123456", test_dir, force_reload=True)

        # should replace existing module_version, not add a new one
        self.assertEqual(ModuleVersion.objects.filter(module__id_name=self.importable_id_name).count(), 1)


    # don't allow loading the same id_name from a different URL. Prevents module replacement attacks, and user confusion
    def test_already_imported(self):
        test_dir = self.fake_github_clone()
        import_module_from_directory("https://github.com/account/importable1", "importable1", "123456", test_dir)

        test_dir = self.fake_github_clone() # import moves files, so get same files again
        with self.assertRaises(ValidationError):
            import_module_from_directory("https://github.com/account/importable2", "importable2", "123456", test_dir)


    # THE BIG TEST. Load a module and test that we can render it correctly
    # This is really an integration test, runs both load and dispatch code
    def test_load_and_dispatch(self):
        test_dir = self.fake_github_clone()

        import_module_from_directory('https://github.com/account/reponame', 'reponame', '123456', test_dir)

        # Module and ModuleVersion should have loaded -- these will raise exception if they don't exist
        module = Module.objects.get(id_name=self.importable_id_name)
        module_version = ModuleVersion.objects.get(module=module)

        # Create a test workflow that uses this imported module
        workflow = add_new_workflow('Dynamic Dispatch Test Workflow')
        wfm = add_new_wf_module(workflow, module_version, order=1)

        # These will fail if we haven't correctly loaded the json describing the parameters
        stringparam = get_param_by_id_name('test', wf_module=wfm)
        colparam = get_param_by_id_name('test_column', wf_module=wfm)
        multicolparam = get_param_by_id_name('test_multicolumn', wf_module=wfm)

        # Does it render right?
        test_csv = 'Class,M,F,Other\n' \
                   'math,10,12,100\n' \
                   'english,,7\,200\n' \
                   'history,11,13,\n' \
                   'economics,20,20,20'
        test_table = pd.read_csv(io.StringIO(test_csv), header=0, skipinitialspace=True)
        test_table_out = test_table.copy()
        test_table_out['M'] *= 2
        test_table_out[['F','Other']] *= 3

        colparam.set_value('M') # double this
        multicolparam.set_value('F,Other') # triple these
        out = module_dispatch_render(wfm, test_table)
        self.assertEqual(wfm.status, WfModule.READY)
        self.assertTrue(out.equals(test_table_out))

        # Test that bad column parameter values are removed
        colparam.set_value('missing_column_name')
        multicolparam.set_value('Other,junk_column_name')
        test_table_out = test_table.copy()
        test_table_out[['Other']] *= 3   # multicolumn parameter has only one valid col
        out = module_dispatch_render(wfm, test_table)
        self.assertEqual(wfm.status, WfModule.READY)
        self.assertTrue(out.equals(test_table_out))

        # if the module crashes, we should get an error with a line number
        stringparam.set_value('crashme')
        out = module_dispatch_render(wfm, test_table)
        self.assertEqual(wfm.status, WfModule.ERROR)


