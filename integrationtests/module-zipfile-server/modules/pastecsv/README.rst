pastecsv
--------

Workbench module that converts text to a table

Developing
----------

First, get up and running:

#. ``docker build .`` # to test

To add a feature:

#. Write a test in ``tests/test_pastecsv.py``
#. Run ``docker build .`` to prove it breaks
#. Edit ``pastecsv.py`` to make the test pass
#. Run ``docker build .`` to prove it works
#. Commit and submit a pull request


To develop continuously on Workbench:

#. Check this code out in a sibling directory to your checked-out Workbench code
#. Start Workbench with ``bin/dev start``
#. In a separate tab in the Workbench directory, run ``bin/dev develop-module pastecsv``
#. Edit this code; the module will be reloaded in Workbench immediately
