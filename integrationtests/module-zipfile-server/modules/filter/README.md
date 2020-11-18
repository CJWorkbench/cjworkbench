# filter

A Workbench module that filters by condition.

# Development

First, set up your enviroment

1. Install `re2` system library:
    * Fedora: `sudo dnf install re2-devel pybind11-devel`
2. Install Tox: `pip3 install tox`
3. Run `tox` to test that everything works

Then do the Development Dance:

1. Write a failing test to `tests/`
2. Run `tox` to test it fails
3. Fix the code so all tests pass
4. Submit a pull request

# Deployment

1. Edit the version in `pyproject.toml`
2. Write an entry to `CHANGELOG.md`
3. Run `tox` one last time
4. `git push`
