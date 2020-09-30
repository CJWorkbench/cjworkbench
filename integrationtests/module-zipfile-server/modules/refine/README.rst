refine
------

Workbench module that cleans inconsistencies and typos across values in seconds using algorithms, or standardizes values manually

Developing
----------

First, get up and running:

#. ``python3 ./setup.py test`` # to test

To add a feature:

#. Write a test in ``test_refine.py``
#. Run ``python3 ./setup.py test`` to prove it breaks
#. Edit ``refine.py`` to make the test pass
#. Run ``python3 ./setup.py test`` to prove it works
#. Commit and submit a pull request

To develop continuously on Workbench:

#. Check this code out in a sibling directory to your checked-out Workbench code
#. Start Workbench with ``bin/dev start``
#. In a separate tab in the Workbench directory, run ``bin/dev develop-module refine``
#. Edit this code; the module will be reloaded in Workbench immediately
