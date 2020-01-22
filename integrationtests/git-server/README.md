Simplified git modules, for integration tests.

Concept
=======

Integration tests shouldn't rely on GitHub: we can't pin versions so our
tests might pass one day and fail the next.

Instead, we set up our own zipfile server. HTTP is the easiest way.

When developing, we put module code in, say, `modules/columnchart`.

An integration test can import `http://module-zipfile-server/columnchart.git`.

(`module-zipfile-server` is an HTTP server running in a background thread of
the Python integration-test runner.)


To Add/Update A Module
======================

1. `./update-module URL`
2. `git status`, `git add .`, etc.

For instance: `./update-module https://github.com/CJWorkbench/columnchart`
will update `modules/columnchart/`


To Add/Update All Modules
=========================

Assuming CJWorkbench authors them all:

`for module in $(ls ./modules); do ./update-module "https://github.com/CJWorkbench/$module.git"; done`


To Use A Module In An Integration Test
======================================

```python
from integrationtests.helpers.modules import import_workbench_module

class MyTest(LoggedInIntegrationTest):
  def test_something(self):
    #... reach the workflows page
    import_workbench_module(self.browser, 'columnchart', 'Column Chart')

  def tearDown(self):
    # This is already run in every LoggedInIntegrationTest tearDown():
    #self.account_admin.clear_modules()


When To Update Modules
======================

When authoring lessons.

Generally, you should integration-test the module in the _module_'s codebase,
not Workbench. The one giant exception is Lessons. Our Lessons depend on
external modules, but the lessons themselves are written in this repository
and so the module code should be in this repository.
