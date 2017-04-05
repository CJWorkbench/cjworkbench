# cjworkbench
A visual dataflow programming system for journalists

To set up a development environment:

- Install (virtualenv)[http://docs.python-guide.org/en/latest/dev/virtualenvs/]
- Install (npm)[https://www.npmjs.com/]
- git clone this repo with submodules: `git clone --recursive https://github.com/jstray/cjworkbench.git`
- `source venv/bin/activate` to use the virtualenv
- `pip install -r requirements.txt` to install Python packages
- `pip install -r requirements-dev.txt` to install packages required for development
- `npm install` to install JavaScript packages
- `python manage.py migrate` to initialize the database
- `python manage.py createsuperuser` if you ever want to login to Django admin (you do)

If you get a message about missing Chartbuilder (probably when running webpack), check that there are files in /chartbuilder/chartbuilder and /chartbuilder/chartbuilder-ui. If these directories are empty, try `git submodule update --init --recursive`

To develop:
- `python manage.py runserver` to start the Django server. It will automatically recompile any .py file you edit.
- `./node_modules/.bin/webpack --config webpack.config.js --watch` to compile JS and CSS whenever changed
- browse to `127.0.0.1:8000/api/initmodules` to load module definitions (needed on first run, or when modules changed)

At the moment the home page `127.0.0.1:8000` does nothing. Go to `127.0.0.1:8000/workflows` to list available workflows.
