histogram
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
