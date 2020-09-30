timestampmath
-------------

Workbench module that compares timestamp columns.

Developing
----------

First, get up and running:

- `tox`

To add a feature:

- Write a test in `test_timestampmath.py`
- Run `tox` to prove it breaks
- Edit `timestampmath.py` to make the test pass
- Run `tox` to prove it works
- Update `CHANGELOG.md`
- Commit and submit a pull request

To develop continuously on Workbench:

- Check this code out in a sibling directory to your checked-out Workbench code
- Start Workbench with `bin/dev start`
- In a separate tab in the Workbench directory, run `bin/dev develop-module timestmapmath`
- Edit this code; the module will be reloaded in Workbench immediately
