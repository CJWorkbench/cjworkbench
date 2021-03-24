Virtual environments
====================

Workbench's modules have very different requirements from its web server. So we
run each process in an appropriate environment.

Prior to 2020-03-22, we used pipenv. It took 10min on a 3.5Ghz processor to
tweak a single dependency.

Now, we use simple venv and pip scripts.

The Gist
========

For environment `venv/ENV`, our environments will run
`python -m pip install --no-deps -r ENV-requirements-frozen.txt`.

Every other file in this directory that we check in to Git is designed to
support this pattern.

Recipes
=======

To install or upgrade a package in the Django environment
---------------------------------------------------------

1. Edit `django-toplevel-requirements.txt`.
2. Run `./freeze-requirements.sh`
3. In our parent directory, re-run `docker build` by, for instance, running
   `bin/dev stop; bin/dev start`.

Notes:

* This upgrades _all_ depencies, not just the one you're editing. For instance,
  `boto3` will get a new version because it's released very frequently. (Pipenv
  does this, too.)
* `django-channels-requirements.txt` is a unique hack. Tread softly around
  Django Channels and `channels_rabbitmq` updates.

To install or upgrade a package in the Django _development_ environment
-----------------------------------------------------------------------

1. Edit `django-dev-requirements.txt`
2. In our parent directory, re-run `docker build` by, for instance, running
   `bin/dev stop; bin/dev start`

Our dev dependencies aren't frozen.

To install or upgrade a package in the cjwkernel environment
------------------------------------------------------------

1. Edit `cjwkernel-toplevel-requirements.txt`.
2. Run `./freeze-requirements.sh`
3. In our parent directory, re-run `docker build` by, for instance, running
   `bin/dev stop; bin/dev start`.

Why is this so slow?
====================

We install everything twice: once to build `requirements-frozen.txt`, and once
in our build/dev Docker images. It's painful, we know.

The slowest parts of installation (and freezing) are A) installing
`build-essential` et al; and B) compiling Python modules. We can resolve both
by building wheels. Our most painful offenders are google-re2, PyICU and
psycopg2.
