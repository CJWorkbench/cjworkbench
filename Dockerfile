# 0.1 parquet-to-arrow: executables we use in Workbench
FROM workbenchdata/parquet-to-arrow:v0.2.0 AS parquet-to-arrow

# 0.2 pybase: Python and tools we use in dev and production
FROM python:3.7.4-slim-buster AS pybase

# We probably don't want these, long-term.
# postgresql-client: because we poll the DB:
# * on prod before ./manage.py migrate
# * on unittest before ./manage.py test
# git: used for importmodulefromgithub
# curl: handy for testing, NLTK download, Watchman download; not worth uninstalling each time
# unzip: to build Watchman ... and [adamhooper, 2019-02-21] I'm afraid
#        to uninstall it after build, in case one of our Python deps shells to it
#
# We do want:
# libcap2: used by forkserver (via ctypes) to drop capabilities
RUN mkdir -p /usr/share/man/man1 /usr/share/man/man7 \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        git \
        postgresql-client \
        libcap2 \
        unzip \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Download NLTK stuff
#
# NLTK expects its data to stay zipped
RUN mkdir -p /usr/share/nltk_data \
    && cd /usr/share/nltk_data \
    && mkdir -p sentiment corpora \
    && curl https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/stopwords.zip > corpora/stopwords.zip \
    && curl https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/sentiment/vader_lexicon.zip > sentiment/vader_lexicon.zip

RUN pip install pipenv==2018.11.26

COPY --from=parquet-to-arrow /usr/bin/parquet-diff /usr/bin/parquet-diff
COPY --from=parquet-to-arrow /usr/bin/parquet-to-arrow /usr/bin/parquet-to-arrow
COPY --from=parquet-to-arrow /usr/bin/parquet-to-arrow-slice /usr/bin/parquet-to-arrow-slice
COPY --from=parquet-to-arrow /usr/bin/parquet-to-text-stream /usr/bin/parquet-to-text-stream

# Set up /app
RUN mkdir /app
WORKDIR /app

# 0.2 Pydev: just for the development environment
FROM pybase AS pydev

# Need build-essential for:
# * regex (TODO nix the dep or make it support manylinux .whl)
# * Twisted - https://twistedmatrix.com/trac/ticket/7945
# * fastparquet
# * python-snappy
# * yajl-py
# * fb-re2
# * watchman (until someone packages binaries)
# * pysycopg2 (binaries are evil because psycopg2 links SSL -- as does Python)
# * thrift-compiler (to generate cjwkernel/thrift/...)
#
# Also:
# * socat: for our dev environment: fetcher uses http://localhost:8000 for in-lesson files
RUN mkdir -p /root/.local/share/virtualenvs \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
      build-essential \
      libsnappy-dev \
      libre2-dev \
      libpq-dev \
      libyajl-dev \
      socat \
      thrift-compiler \
    && rm -rf /var/lib/apt/lists/*

# build watchman. Someday let's hope someone publishes binaries
# https://facebook.github.io/watchman/docs/install.html
RUN cd /tmp \
    && curl -L https://github.com/facebook/watchman/archive/v4.9.0.zip > watchman-4.9.0.zip \
    && unzip watchman-4.9.0.zip \
    && cd watchman-4.9.0 \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
      libssl-dev \
      autoconf \
      automake \
      libtool \
      libpcre3-dev \
      pkg-config \
    && ./autogen.sh \
    && ./configure --prefix=/usr --enable-lenient \
    && make -j4 \
    && make install \
    && cd /tmp \
    && rm -rf /tmp/watchman-4.9.0* \
    && apt-get remove --purge -y \
      libssl-dev \
      autoconf \
      automake \
      libtool \
      libpcre3-dev \
      pkg-config \
    && apt-get autoremove --purge -y \
    && rm -rf /var/lib/apt/lists/*

# Add "mc" command, so we can create a non-root user in minio (for STS).
RUN true \
    && curl https://dl.min.io/client/mc/release/linux-amd64/archive/mc.RELEASE.2019-09-24T01-36-20Z -o /usr/bin/mc \
    && chmod +x /usr/bin/mc

# Add a Python wrapper that will help PyCharm cooperate with pipenv
# See https://blog.jetbrains.com/pycharm/2015/12/using-docker-in-pycharm/ for
# PyCharm's expectations. Just set "Python interpreter path" to
# "pipenv-run-python" to ensure:
#
# * `cd /app`: PyCharm mounts the source tree to `/opt/project` and overwrites
#              the current working directory. We force `cd /app` to restore
#              what the Dockerfile already specifies. That's important because
#              `pipenv` looks for packages in a virtualenv named after the
#              current working directory.
#
# * `exec pipenv run python "$@"`: PyCharm does not let us specify a command
#                                  for Docker to run. It only lets us specify
#                                  "Python interpreter path." This wrapper will
#                                  provide the interface PyCharm expects, with
#                                  the environment variables Python needs to
#                                  find our virtualenv.
#
# Why do we create the file with RUN instead of COPY? Because even in 2018,
# COPY does not copy the executable bit on Windows, so we need a RUN anyway
# to make it executable.
RUN true \
    && echo '#!/bin/sh\ncd /app\nexec pipenv run python "$@"' >/usr/bin/pipenv-run-python \
    && chmod +x /usr/bin/pipenv-run-python

# 1. Python deps -- which rarely change, so this part of the Dockerfile will be
# cached (when building locally)
FROM pybase AS pybuild

# Install Python dependencies. They rarely change.
# For Docker images we install them to the local system, not to a virtualenv.
# Containers don't use pipenv.
COPY Pipfile Pipfile.lock /app/

# Need build-essential for:
# * regex (TODO nix the dep or make it support manylinux .whl)
# * Twisted - https://twistedmatrix.com/trac/ticket/7945
# * fastparquet
# * python-snappy
# * yajl-py
# * pysycopg2 (binaries are evil because psycopg2 links SSL -- as does Python)
# ... and we want to keep libsnappy and yajl around after the fact, too
RUN true \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
      build-essential \
      libsnappy1v5 \
      libsnappy-dev \
      libre2-5 \
      libre2-dev \
      libpq-dev \
      libyajl2 \
      libyajl-dev \
    && pipenv install --dev --system --deploy \
    && apt-get remove --purge -y \
      build-essential \
      libsnappy-dev \
      libre2-dev \
      libpq-dev \
    && apt-get autoremove --purge -y \
    && rm -rf /var/lib/apt/lists/*


# 2. Node deps -- completely independent
# 2.1 jsbase: what we use in dev-in-docker
FROM node:12.9.0-buster-slim as jsbase

RUN mkdir /app
WORKDIR /app

# 2.2 jsbuild: where we build JavaScript assets
FROM jsbase AS jsbuild

COPY package.json package-lock.json /app/
RUN npm install

COPY webpack.config.js setupJest.js /app/
COPY __mocks__/ /app/__mocks__/
COPY assets/ /app/assets/
# Inject unit tests into our continuous integration
# This catches mistakes that would otherwise foil us in bin/integration-test;
# and currently we rely on this line in our CI scripts (cloudbuild.yaml).
RUN npm test
RUN npm run lint
RUN node_modules/.bin/webpack -p


# 3. Three prod servers will all be based on the same stuff:
FROM pybuild AS base

# Configure Black
COPY pyproject.toml pyproject.toml

COPY cjwkernel/ /app/cjwkernel/
COPY cjwstate/ /app/cjwstate/
COPY cjworkbench/ /app/cjworkbench/
COPY staticmodules/ /app/staticmodules/
# TODO make server/ frontend-specific
COPY server/ /app/server/
# cron/, fetcher/ and renderer/ are referenced in settings.py, so they must be
# in all Django apps. TODO make them _not_ Django apps. (change ORM)
COPY cron/ /app/cron/
COPY fetcher/ /app/fetcher/
COPY renderer/ /app/renderer/
COPY bin/ /app/bin/
COPY manage.py /app/
# templates are used in renderer for notifications emails and in frontend for
# views. TODO move renderer templates elsewhere.
COPY templates/ /app/templates/
COPY assets/locale/ /app/assets/locale/
# Inject code-style tests into our continuous integration.
# This catches style errors that accidentally got past somebody's
# pre-commit hook.
RUN black --check /app

# 3.1. migrate: runs ./manage.py migrate
FROM base AS migrate
# assets/ is static files. migrate will upload them to minio.
COPY assets/ /app/assets/
COPY --from=jsbuild /app/assets/bundles/ /app/assets/bundles/
CMD [ "bin/migrate-prod" ]

# 3.2. fetcher: runs fetch
FROM base AS fetcher
CMD [ "./manage.py", "fetcher" ]

# 3.3. fetcher: runs fetch
FROM base AS renderer
CMD [ "./manage.py", "renderer" ]

# 3.4. cron: schedules fetches and runs cleanup SQL
FROM base AS cron
CMD [ "./manage.py", "cron" ]

# 3.5. frontend: serves website
FROM base AS frontend
COPY --from=jsbuild /app/webpack-stats.json /app/
# 8080 is Kubernetes' conventional web-server port
EXPOSE 8080
# TODO serve static files elsewhere
# Beware: our daphne does not serve static files! Use migrate-prod to push them
# to GCS and publish them there.
#
# We set application-close-timeout to something enormous. Otherwise, Daphne will
# call `task.cancel()` on a long-running, closed connection. That's
# catastrophic: if the Websocket connection is subscribed to a group, then the
# group's messages will queue up until they fill our channel layer -- causing
# back-pressure, meaning _all Websocket connections stop working_. (At the same
# time, if the application never dies at all we have another error. So keep
# --application-close-timeout small enough that we'll get a warning when there's
# a bug in our code.)
CMD [ "daphne", "-b", "0.0.0.0", "-p", "8080", "--application-close-timeout", "180", "cjworkbench.asgi:application" ]
