Columnchart
---------

Workbench module that presents a numbers as columns.

Developing
----------

First, get up and running:

1. ``pip3 install pipenv``
2. ``pipenv sync`` # to download dependencies
3. ``pipenv run ./setup.py test`` # to test

To add a feature on the Python side:

1. Write a test in ``tests/``
2. Run ``pipenv run ./setup.py test`` to prove it breaks
3. Edit ``columnchart.py`` to make the test pass
4. Run ``pipenv run ./setup.py test`` to prove it works
5. Commit and submit a pull request

To add a feature on the HTML/JavaScript side:

1. Edit ``columnchart.html``
2. Test by importing the module from this directory into Workbench
3. Commit and submit a pull request

To develop continuously on Workbench:

1. Check out the columnchart repository in a sibling directory to your checked-out Workbench code.
2. Start Workbench with ``bin/dev start``
3. In a separate tab in the Workbench directory, run ``bin/dev develop-module columnchart``
4. Edit this code; the module will be reloaded in Workbench immediately
5. When viewing the chart in Workbench, modify parameters to re-render JSON and refresh the page to load new HTML
