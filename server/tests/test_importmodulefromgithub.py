from server.importmodulefromgithub import *
from server.tests.utils import *
from pathlib import Path

import mock

import json, os, shutil

# Patch get_already_imported from importmodulefromgithub
def overriden_get_already_imported():
    return {
        "accio": "www.github.com/something",
        "lumos": ""
    }

class ImportFromGitHubTest(LoggedInTestCase):
    def setUp(self):
        super(ImportFromGitHubTest, self).setUp()  # log in
        self.cleanup()

    def tearDown(self):
        super(ImportFromGitHubTest, self).tearDown()
        self.cleanup()

    def cleanup(self):
        pwd = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')):
            shutil.rmtree(os.path.join(pwd, 'prototype-dynamic-loading'))
        if os.path.isdir(os.path.join(pwd, '..', '..', 'importedmodules', 'prototype-dynamic-loading')):
            shutil.rmtree(os.path.join(pwd, '..', '..', 'importedmodules', 'prototype-dynamic-loading'))


    def test_sanitise_url(self):
        #test valid url
        input_url = "https://github.com/anothercookiecrumbles/prototype-dynamic-loading"
        returned_url = sanitise_url(input_url)
        self.assertEqual(input_url, returned_url, "In this case, the input url doesn't need to be cleaned. Therefore " +
                         " the output {} should be the input {}.".format(returned_url, input_url))

        #test valid url with a git suffix
        input_url_git = "https://github.com/anothercookiecrumbles/prototype-dynamic-loading.git"
        returned_url_git = sanitise_url(input_url_git)
        self.assertEqual(input_url, returned_url_git, "In this case, the input url should have .git stripped out.")

        #test valid url with padding (i.e. extra spaces)
        input_url_spaces = "     https://github.com/anothercookiecrumbles/prototype-dynamic-loading"
        returned_url_spaces = sanitise_url(input_url)
        self.assertEqual(input_url, returned_url_spaces, "In this case, the input url just needs to be trimmed."
                "Therefore the output {} should be the trimmed input {}.".format(returned_url, input_url_spaces))

        input_url_spaces = "     https://github.com/anothercookiecrumbles/prototype-dynamic-loading     "
        returned_url_spaces = sanitise_url(input_url)
        self.assertEqual(input_url, returned_url_spaces, "In this case, the input url needs to be trimmed. "
                    "Therefore the output {} should be the input trimmed {}.".format(returned_url, input_url_spaces))

        #test valid url, invalid github url
        input_url = "www.testmeifyoucan.com"
        with self.assertRaisesMessage(ValidationError, 'Invalid GitHub URL entered: http://%s' % (input_url)):
            sanitise_url(input_url)

        input_url = "http://www.testmeifyoucan.com"
        with self.assertRaisesMessage(ValidationError, 'Invalid GitHub URL entered: %s' % (input_url)):
            sanitise_url(input_url)

        #test empty string
        input_url = ""
        with self.assertRaisesMessage(ValidationError, 'Empty URL entered.'):
            sanitise_url(input_url)

        input_url = "    " #non-trimmed empty string
        with self.assertRaisesMessage(ValidationError, 'Empty URL entered.'):
            sanitise_url(input_url)

        #test non-url
        input_url = "this is not a url"
        with self.assertRaisesMessage(ValidationError, 'Invalid GitHub URL entered: %s' % (input_url)):
            sanitise_url(input_url)

    def test_retrieve_project_name(self):
        #Here, we assume that we have a _clean_/_sanitised_ URL; if we didn't, the code should've thrown an exception
        #earlier in the stack. Hence, we don't test _bad_ urls.

        #retrieve project name for a GitHub url, but one that doesn't end .git.
        git_url = "https://github.com/anothercookiecrumbles/prototype-dynamic-loading"
        project_name = retrieve_project_name(git_url)
        self.assertEqual(project_name, "prototype-dynamic-loading")

    def setup_module_structure(self, pwd):
        test_dir = os.path.join(pwd, 'prototype-dynamic-loading')
        if os.path.isdir(test_dir):
            shutil.rmtree(test_dir)
        shutil.copytree(os.path.join(pwd, 'test_data/importable'), test_dir)

    def test_validate_module_structure(self):
        # OK, this seems gross, but it's necessary. We don't want to rely on a remote repo existing, so we're going
        # to have to drive this test off a local repo that fits the structure that we expect whilst importing a module
        # from GitHub.
        pwd = os.path.dirname(os.path.abspath(__file__))
        test_dir = os.path.join(pwd, 'prototype-dynamic-loading')

        # Test on valid git repo structure
        self.setup_module_structure(pwd)
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
        self.setup_module_structure(pwd)
        more_json = os.path.join(test_dir, 'disposable.json')
        open(more_json, 'a').close()
        # ensure that disposable.json is created – we need this for the tests to run properly.
        self.assertTrue(os.path.isfile(more_json),
                        "disposable.json must be created in order for these unit tests to run properly.")

        with self.assertRaisesMessage(ValidationError, "Multiple files exist with extension json. This isn't currently"+
                                                       " supported"):
            mapping = validate_module_structure(test_dir)


        # Add additional Python file directory, assert this fails
        self.setup_module_structure(pwd)
        open(os.path.join(test_dir, 'disposable.py'), 'a').close()
        # ensure that disposable.py is created – we need this for the tests to run properly.
        self.assertTrue(os.path.isfile(os.path.join(pwd, 'prototype-dynamic-loading', 'disposable.py')),
                        "disposable.py must be created in order for these unit tests to run properly.")

        with self.assertRaises(ValidationError):
            mapping = validate_module_structure(test_dir)

        # Test invalid modules: 2/ ensure that at least one Python and one JSON file exist.
        self.setup_module_structure(pwd)
        os.remove(os.path.join(test_dir, 'importable.json'))
        with self.assertRaises(ValidationError):
            mapping = validate_module_structure(test_dir)

        self.setup_module_structure(pwd)
        os.remove(os.path.join(test_dir, 'importable.py'))
        with self.assertRaises(ValidationError):
            mapping = validate_module_structure(test_dir)


    def test_extract_version_hash(self):
        pwd = os.path.dirname(os.path.abspath(__file__))
        self.setup_module_structure(pwd)
        curdir = os.path.join(pwd, 'prototype-dynamic-loading')
        os.rename(os.path.join(curdir, 'git'),
                  os.path.join(curdir, '.git'))
        self.assertTrue(os.path.isdir(os.path.join(curdir, ".git")))
        version = extract_version(curdir)
        shutil.rmtree(curdir)
        self.assertEquals(version, '7832830',
                          "The hash of the git repo should be {}, but the function returned {}.".format('427847c',
                                                                                                        version))

    @mock.patch('server.importmodulefromgithub.get_already_imported', side_effect=overriden_get_already_imported)
    def test_validate_json(self, get_already_imported_function):
        pwd = os.path.dirname(os.path.abspath(__file__))
        self.setup_module_structure(pwd)
        test_dir = os.path.join(pwd, "prototype-dynamic-loading")

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

        # ensure error if module is already loaded.
        # whilst this is artificially loading an item in the system, it's a reasonable way to do a unit test for potential _real_ modules.
        sys.modules['server.modules.importable'] = ""
        # amend underlying JSON file
        open_file = open(os.path.join(test_dir, 'importable.json'))
        try:
            module_config = json.load(open_file)
            module_config['id_name'] = "lumos"
        finally:
            open_file.close()

        with open(os.path.join(test_dir, 'importable.json'), "w") as writable:
            json.dump(module_config, writable)
        with self.assertRaisesMessage(ValidationError, "Module lumos has already been loaded, and its source is Internal."):
            get_module_config_from_json("someurl", mapping, test_dir)


    def test_destination_directory_name(self):
        pwd = os.path.dirname(os.path.abspath(__file__))

        #check valid scenario
        self.setup_module_structure(pwd)
        module_directory = os.path.join(pwd, "..", "..", "importedmodules/prototype-dynamic-loading")
        destination_directory = destination_directory_name(module_directory, "123456")
        self.assertTrue(Path(destination_directory) == Path(pwd) / "../../importedmodules/prototype-dynamic-loading/123456",
                "The destination directory should be {}/prototype-dynamic-loading/123456".format(pwd + "/../../importedmodules") +
                " but it's {}".format(destination_directory))

        # should work even if files already exists for the given module-version combination
        # in which case the dir should be deleted, so as to be ready for re-import
        os.makedirs(destination_directory)
        destination_directory_name(module_directory,"123456")
        self.assertFalse(os.path.isdir(destination_directory))


    def test_add_boilerplate_and_check_syntax(self):
        #setup things like the destination directory and everything else –
        #this is kinda tedious...
        pwd = os.path.dirname(os.path.abspath(__file__))
        destination_directory = os.path.join(pwd, "../../importedmodules/prototype-dynamic-loading/123456")
        test_dir = os.path.join(pwd, "prototype-dynamic-loading")
        self.setup_module_structure(pwd)
        os.makedirs(destination_directory)

        shutil.copy(os.path.join(test_dir, "importable.py"), destination_directory)

        # test valid scenario. Failures should raise ValidationError
        compiled = add_boilerplate_and_check_syntax(destination_directory, "importable.py")
        shutil.rmtree(destination_directory)
        shutil.rmtree(test_dir)

        # test invalid scenario: what if Python file doesn't exist.
        self.setup_module_structure(pwd)
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
        pwd = os.path.dirname(os.path.abspath(__file__))
        destination_directory = os.path.join(pwd, "../../importedmodules/prototype-dynamic-loading/123456")

        test_dir = os.path.join(pwd, "prototype-dynamic-loading")

        self.setup_module_structure(pwd)
        os.makedirs(destination_directory)

        #test valid scenario
        shutil.copy(os.path.join(test_dir, "importable.py"), destination_directory)
        add_boilerplate_and_check_syntax(destination_directory, "importable.py")  # adds crucial boilerplate to the file
        imported_class = validate_python_functions(destination_directory, "importable.py")
        self.assertTrue(type(imported_class[1]) == type, "The module must be importable, and be of type 'type'.")

        #test invalid scenario: > 1 class
        # shutil.copy(os.path.join(pwd, "test_data", "unimportable_multiclass.py"),  destination_directory)
        # with self.assertRaisesMessage(ValidationError, "Multiple classes exist in python file."):
        #     validate_python_functions(destination_directory, pwd, "prototype-dynamic-loading",
        #                                            "unimportable_multiclass.py")
