histogram
---------

Workbench module that present number series as lines.

Developing
----------

First, get up and running:

`tox`

This will download dependencies and run tests. It should pass.

To add a feature on the Python side:

1. Write a test in `tests/`
2. Run `tox` to prove it breaks
3. Edit `linechart.py` to make the test pass
4. Run `tox` to prove it works
5. Commit and submit a pull request

To add a feature on the HTML/JavaScript side:

1. Edit `linechart.html`
2. Test by importing the module from this directory into Workbench
3. Commit and submit a pull request

To develop continuously on Workbench:

1. Check this code out in a sibling directory to your checked-out Workbench code
1. Start Workbench with `bin/dev start`
2. In a separate tab in the Workbench directory, run `bin/dev develop-module linechart`
3. Edit this code; the module will be reloaded in Workbench immediately
4. When viewing the chart in Workbench, modify parameters to re-render JSON and refresh the page to load new HTML
