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
        shutil.copytree(os.path.join(pwd, 'test_data/importable'), os.path.join(pwd, 'prototype-dynamic-loading'))

    def test_validate_module_structure(self):
        #OK, this seems gross, but it's necessary. We don't want to rely on a remote repo existing, so we're going
        #to have to drive this test off a local repo that fits the structure that we expect whilst importing a module
        #from GitHub.

        pwd = os.path.dirname(os.path.abspath(__file__))
        self.setup_module_structure(pwd)
        mapping = validate_module_structure(pwd, pwd, 'prototype-dynamic-loading')
        self.assertTrue(len(mapping) == 2, "We should only have two files in the module structure: one Python " +
                        "and one JSON.")
        self.assertTrue("json" in mapping, "A json file must exist in the module structure.")
        self.assertTrue("py" in mapping, "A python file must exist in the module structure.")
        self.assertTrue(mapping["py"] == "importable.py", "The py mapping in the module must be against the only " +
                                                        "Python file in the directory: importable.py.")
        self.assertTrue(mapping["json"] == "importable.json", "The json mapping in the module must be against the only JSON" +
                        " file in the directory: importable.json")


        #Test invalid modules: 1/ ensure only one Python and one JSON file exist.
        #Add additional JSON file to directory.
        open(os.path.join(pwd, 'prototype-dynamic-loading', 'disposable.json'), 'a').close()

        # ensure that "GitHub" repo exists.
        self.assertTrue(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')))
        #ensure that disposable.json is created – we need this for the tests to run properly.
        self.assertTrue(os.path.isfile(os.path.join(pwd, 'prototype-dynamic-loading', 'disposable.json')),
                        "disposable.json must be created in order for these unit tests to run properly.")

        with self.assertRaisesMessage(ValidationError, "Multiple files exist with extension json. This isn't currently"+
                                                       " supported"):
            mapping = validate_module_structure(pwd, pwd, 'prototype-dynamic-loading')

        self.assertFalse(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')),
                         "The ValidationError raised due to the extra json file should've purged the repository as " +
                         " part of standard clean-up, to ensure we don't have orphan files and repos lying around.")

        #Add additional Python file directory.
        self.setup_module_structure(pwd) # we need to re-copy the folder over as it was cleaned up in the last step.
        open(os.path.join(pwd, 'prototype-dynamic-loading', 'disposable.py'), 'a').close()
        # ensure that "GitHub" repo exists.
        self.assertTrue(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')))
        # ensure that disposable.py is created – we need this for the tests to run properly.
        self.assertTrue(os.path.isfile(os.path.join(pwd, 'prototype-dynamic-loading', 'disposable.py')),
                        "disposable.json must be created in order for these unit tests to run properly.")

        with self.assertRaisesMessage(ValidationError,
                                      "Multiple files exist with extension py. This isn't currently supported"):
            mapping = validate_module_structure(pwd, pwd, 'prototype-dynamic-loading')
        self.assertFalse(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')),
                         "The ValidationError raised due to the extra py file should've purged the repository as " +
                         " part of standard clean-up, to ensure we don't have orphan files and repos lying around.")


        #Test invalid modules: 2/ ensure that at least one Python and one JSON file exist.
        self.setup_module_structure(pwd) # we need to re-copy the folder over as it was cleaned up in the last step.
        os.remove(os.path.join(pwd, 'prototype-dynamic-loading', 'importable.json'))
        with self.assertRaisesMessage(ValidationError, "prototype-dynamic-loading is not a valid workflow module."):
            mapping = validate_module_structure(pwd, pwd, 'prototype-dynamic-loading')
        self.assertFalse(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')),
                         "The ValidationError raised due to the missing json file should've purged the repository as " +
                         " part of standard clean-up, to ensure we don't have orphan files and repos lying around.")

        self.setup_module_structure(pwd)  # we need to re-copy the folder over as it was cleaned up in the last step.
        os.remove(os.path.join(pwd, 'prototype-dynamic-loading', 'importable.py'))
        with self.assertRaisesMessage(ValidationError, "prototype-dynamic-loading is not a valid workflow module."):
            mapping = validate_module_structure(pwd, pwd, 'prototype-dynamic-loading')
        self.assertFalse(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')),
                         "The ValidationError raised due to the missing py file should've purged the repository as " +
                         " part of standard clean-up, to ensure we don't have orphan files and repos lying around.")

        self.setup_module_structure(pwd) # we need to re-copy the folder over as it was cleaned up in the last step.
        open(os.path.join(pwd, 'prototype-dynamic-loading', 'additional_file'), 'a').close()
        os.remove(os.path.join(pwd, 'prototype-dynamic-loading', 'importable.json'))
        with self.assertRaisesMessage(ValidationError, "prototype-dynamic-loading is not a valid workflow module. " +
                "You must have at least one .py file and one .json file."):
            mapping = validate_module_structure(pwd, pwd, 'prototype-dynamic-loading')
        self.assertFalse(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')),
                         "The ValidationError raised due to missing mandatory file should've purged the repository " +
                         "as part of standard clean-up, to ensure we don't have orphan files and repos lying around.")

    def test_extract_version_hash(self):
        pwd = os.path.dirname(os.path.abspath(__file__))
        self.setup_module_structure(pwd)
        os.rename(os.path.join(pwd, 'prototype-dynamic-loading','git'), os.path.join(pwd, 'prototype-dynamic-loading',
                                                                                     '.git'))
        self.assertTrue(os.path.isdir(os.path.join(pwd, "prototype-dynamic-loading", ".git")))
        version = extract_version(pwd, "prototype-dynamic-loading")
        shutil.rmtree(os.path.join(pwd, "prototype-dynamic-loading"))
        self.assertEquals(version, '7832830',
                          "The hash of the git repo should be {}, but the function returned {}.".format('427847c',
                                                                                                        version))

    @mock.patch('server.importmodulefromgithub.get_already_imported', side_effect=overriden_get_already_imported)
    def test_validate_json(self, get_already_imported_function):
        pwd = os.path.dirname(os.path.abspath(__file__))
        self.setup_module_structure(pwd)
        test_dir = os.path.join(pwd, "prototype-dynamic-loading")
        mapping = {}
        #ensure we get a ValidationError if the mapping doesn't have a json key.
        with self.assertRaisesMessage(ValidationError, "No JSON file found in remote repository."):
            validate_json("", mapping, pwd, "prototype-dynamic-loading")
        self.assertFalse(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')),
                         "Repository should be deleted on ValidationError (missing json key).")

        #check valid scenario, i.e. the system successfully parses the JSON configuration.
        self.setup_module_structure(pwd)
        mapping = {'json': 'importable.json', 'py': 'importable.py'}
        module_config, json_file = validate_json("", mapping, pwd, "prototype-dynamic-loading")
        self.assertTrue(json_file == 'importable.json', "The json file should be importable.json.")
        self.assertTrue(len(module_config) == 5, 'The configuration should have loaded 5 items, but it loaded ' +
                                                 ' {} items.'.format(len(module_config)))
        self.assertTrue(all (k in module_config for k in ("id_name", "description", "name", "category", "parameters")),
                        "Not all mandatory keys exist in the module_config/json file.")

        # ensure error if module is already loaded.
        # whilst this is artificially loading an item in the system, it's a reasonable way to do a unit test for potential _real_ modules.
        sys.modules['server.modules.importable'] = ""
        # amend underlying JSON file
        open_file = open(os.path.join(pwd, 'prototype-dynamic-loading', 'importable.json'))
        try:
            module_config = json.load(open_file)
            module_config['id_name'] = "lumos"
        finally:
            open_file.close()

        with open(os.path.join(pwd, 'prototype-dynamic-loading', 'importable.json'), "w") as writable:
            json.dump(module_config, writable)
        with self.assertRaisesMessage(ValidationError, "Module lumos has already been loaded, and its source is Internal."):
            validate_json("someurl", mapping, pwd, "prototype-dynamic-loading")
        self.assertFalse(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')),
                         "Repository should be deleted on module already being loaded into the system.")


    def test_validate_python(self):
        pwd = os.path.dirname(os.path.abspath(__file__))
        self.setup_module_structure(pwd)
        mapping = {}
        # ensure we get a ValidationError if the mapping doesn't have a json key.
        with self.assertRaisesMessage(ValidationError, "No Python file found in remote repository."):
            validate_python(mapping, pwd, "../../importedmodules/", "prototype-dynamic-loading", "123456")
        self.assertFalse(os.path.isdir(os.path.join(pwd, 'prototype-dynamic-loading')),
                         "Repository should be deleted on ValidationError (missing json key).")

        #check valid scenario
        self.setup_module_structure(pwd)
        mapping = {'json': 'importable.json', 'py': 'importable.py'}
        module_directory = os.path.join(pwd, "..", "..", "importedmodules")
        python_file, destination_directory = \
            validate_python(mapping, pwd, module_directory, "prototype-dynamic-loading", "123456")

        self.assertTrue(python_file == 'importable.py', "The python file should be importable.py")
        self.assertTrue(Path(destination_directory) == Path(pwd) / "../../importedmodules/prototype-dynamic-loading/123456",
                "The destination directory should be {}/prototype-dynamic-loading/123456".format(pwd + "/../../importedmodules") +
                " but it's {}".format(destination_directory))

        # should work even if files already exists for the given module-version combination
        # in which case the dir should be deleted, so as to be ready for re-import
        os.makedirs(destination_directory)
        validate_python(mapping, pwd, module_directory, "prototype-dynamic-loading", "123456")
        self.assertFalse(os.path.isdir(destination_directory))


    def test_compile_python(self):
        #setup things like the json directory and the python directory and everything else –
        #this is kinda tedious...
        pwd = os.path.dirname(os.path.abspath(__file__))
        destination_directory = os.path.join(pwd, "../../importedmodules/prototype-dynamic-loading/123456")

        test_dir = os.path.join(pwd, "prototype-dynamic-loading")

        self.setup_module_structure(pwd)
        os.makedirs(destination_directory)

        shutil.copy(os.path.join(test_dir, "importable.py"), destination_directory)

        #test valid scenario
        compiled = compile_python(destination_directory, pwd, "prototype-dynamic-loading", "importable.py")
        #I don't know if there's a better way of doing this, but for now, I'm just checking if the compile process
        #returns a *pyc file.
        self.assertTrue(compiled.endswith("pyc"), "{} should've compiled to a pyc file.".format("importable.py"))
        shutil.rmtree(destination_directory)
        shutil.rmtree(test_dir)

        #test invalid scenario: what if Python file doesn't exist.
        self.setup_module_structure(pwd)
        os.makedirs(destination_directory)

        with self.assertRaisesMessage(ValidationError, "Unable to open {}.".format("importable.py")):
            compiled = compile_python(destination_directory, pwd, "prototype-dynamic-loading", "importable.py")
        #ensure cleanup's happened
        self.assertFalse(os.path.isdir(test_dir), "{} should've been deleted as part of clean-up".format(test_dir))
        self.assertFalse(os.path.isdir(destination_directory), "{} should've been deleted as part of clean-up".format(destination_directory))

        #test invalid scenario: what if Python file exists but can't be compiled.
        self.setup_module_structure(pwd)
        os.makedirs(destination_directory)

        # create file and add some random content to file
        f = open(os.path.join(pwd, 'prototype-dynamic-loading', 'additional_file.py'), 'a')
        f.write("random content here")
        f.close()

        shutil.copy(os.path.join(test_dir, "additional_file.py"), destination_directory)

        with self.assertRaisesMessage(ValidationError, "Unable to compile {}.".format("additional_file.py")):
            compiled = compile_python(destination_directory, pwd, "prototype-dynamic-loading", "additional_file.py")
            # ensure cleanup's happened
        self.assertFalse(os.path.isdir(test_dir), "{} should've been deleted as part of clean-up".format(test_dir))
        self.assertFalse(os.path.isdir(destination_directory), "{} should've been deleted as part of clean-up".format(destination_directory))

    def test_validate_python_functions(self):
        pwd = os.path.dirname(os.path.abspath(__file__))
        destination_directory = os.path.join(pwd, "../../importedmodules/prototype-dynamic-loading/123456")

        test_dir = os.path.join(pwd, "prototype-dynamic-loading")

        self.setup_module_structure(pwd)
        os.makedirs(destination_directory)

        #test valid scenario
        shutil.copy(os.path.join(test_dir, "importable.py"), destination_directory)
        imported_class = validate_python_functions(destination_directory, pwd, "prototype-dynamic-loading", "importable.py")
        self.assertTrue(type(imported_class[1]) == type, "The module must be importable, and be of type 'type'.")

        #test invalid scenario: > 1 class
        # shutil.copy(os.path.join(pwd, "test_data", "unimportable_multiclass.py"),  destination_directory)
        # with self.assertRaisesMessage(ValidationError, "Multiple classes exist in python file."):
        #     validate_python_functions(destination_directory, pwd, "prototype-dynamic-loading",
        #                                            "unimportable_multiclass.py")
