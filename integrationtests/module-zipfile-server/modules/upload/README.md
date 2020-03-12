upload
------

Workbench module that uploads CSV, Excel or JSON files from your computer

Developing
----------

First, get up and running:

- `docker build .` # to test

To add a feature:

- Write a test in `test_upload.py`
- Run `docker build .` to prove it breaks
- Edit `upload.py` to make the test pass
- Run `docker build .` to prove it works
- Commit and submit a pull request


To develop continuously on Workbench:

- Check this code out in a sibling directory to your checked-out Workbench code
- Start Workbench with `bin/dev start`
- In a separate tab in the Workbench directory, run `bin/dev develop-module upload`
- Edit this code; the module will be reloaded in Workbench immediately
