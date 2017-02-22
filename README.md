# cjworkbench
A visual dataflow programming system for journalists

To set up a development environment:

- Install (virtualenv)[http://docs.python-guide.org/en/latest/dev/virtualenvs/]
- Install (npm)[https://www.npmjs.com/]
- git clone this repo
- `source newenv/bin/activate` to use the virtualenv
- `pip install -r requirements.txt` to install Python packages
- `pip install -r requirements-dev.txt` to install packages required for development
- `npm install` to install JavaScript packages
- `python manage.py createsuperuser` if you ever want to login to Django admin (you do)
- `python manage.py migrate` to initialize the database

To develop:
- `python manage.py runserver` to start the Django server. It will automatically recompile any .py file you edit.
- `./node_modules/.bin/webpack --config webpack.config.js --watch` to compile JS and CSS whenever changed

