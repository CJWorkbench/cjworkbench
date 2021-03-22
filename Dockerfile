# 0.1 parquet-to-arrow: executables we use in Workbench
FROM workbenchdata/parquet-to-arrow:v2.1.0 AS parquet-to-arrow
FROM workbenchdata/arrow-tools:v1.0.0 AS arrow-tools

# 0.2 pybase: Python and tools we use in dev and production
FROM python:3.8.5-slim-buster AS pybase

# We probably don't want these, long-term.
# curl: handy for testing, NLTK download; not worth uninstalling each time
# unzip: [adamhooper, 2019-02-21] I'm afraid to uninstall it, in case one
#        of our Python deps shells to it
#
# We do want:
# postgresql-client: for pg_isready in startup scripts:
# * on prod, in bin/*-prod
# * on unittest before ./manage.py test
# libcap2: used by pyspawner (via ctypes) to drop capabilities
# iproute2: used by setup-sandboxes.sh to find our IP for NAT
# iptables: used by setup-sandboxes.sh to set up NAT and firewall
# libicu63: used by PyICU
# libre2-5: used by google-re2 (in modules)
RUN mkdir -p /usr/share/man/man1 /usr/share/man/man7 \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        iproute2 \
        iptables \
        libcap2 \
        libicu63 \
        libre2-5 \
        postgresql-client \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Download NLTK stuff
#
# NLTK expects its data to stay zipped
RUN mkdir -p /usr/share/nltk_data \
    && cd /usr/share/nltk_data \
    && mkdir -p sentiment corpora \
    && curl https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/stopwords.zip > corpora/stopwords.zip \
    && curl https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/sentiment/vader_lexicon.zip > sentiment/vader_lexicon.zip

RUN pip install pipenv==2020.8.13

COPY --from=arrow-tools /usr/bin/arrow-validate /usr/bin/arrow-validate
COPY --from=arrow-tools /usr/bin/csv-to-arrow /usr/bin/csv-to-arrow
COPY --from=arrow-tools /usr/bin/json-to-arrow /usr/bin/json-to-arrow
COPY --from=arrow-tools /usr/bin/xls-to-arrow /usr/bin/xls-to-arrow
COPY --from=arrow-tools /usr/bin/xlsx-to-arrow /usr/bin/xlsx-to-arrow
COPY --from=parquet-to-arrow /usr/bin/parquet-diff /usr/bin/parquet-diff
COPY --from=parquet-to-arrow /usr/bin/parquet-to-arrow /usr/bin/parquet-to-arrow
COPY --from=parquet-to-arrow /usr/bin/parquet-to-text-stream /usr/bin/parquet-to-text-stream

# Set up /app
RUN mkdir /app
WORKDIR /app

# 0.2 Pydev: just for the development environment
FROM workbenchdata/watchman-bin:v0.0.1-buster-slim AS watchman-bin
FROM pybase AS pydev

# Need build-essential for:
# * regex (TODO nix the dep or make it support manylinux .whl)
# * google-re2
# * pysycopg2 (binaries are evil because psycopg2 links SSL -- as does Python)
# * PyICU
#
# Need libre2-dev to build google-re2
# Need pkg-config to build PyICU
# Need pybind11-dev to build google-re2
RUN mkdir -p /root/.local/share/virtualenvs \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
      build-essential \
      libicu-dev \
      libpq-dev \
      libre2-dev \
      pkg-config \
      pybind11-dev \
    && rm -rf /var/lib/apt/lists/*

# Add "watchman" command -- we use it in dev mode to monitor for source code changes
COPY --from=watchman-bin /usr/bin/watchman /usr/bin/watchman
COPY --from=watchman-bin /usr/var/run/watchman /usr/var/run/watchman

COPY cjwkernel/setup-chroot-layers.sh /tmp/setup-chroot-layers.sh
RUN /tmp/setup-chroot-layers.sh && rm /tmp/setup-chroot-layers.sh

COPY bin/unittest-entrypoint.sh /app/bin/unittest-entrypoint.sh

# Let chroots overlay the root FS -- meaning they must be on another FS.
# see cjwkernel/setup-sandboxes.sh
VOLUME /var/lib/cjwkernel/chroot

# 1. Python deps -- which rarely change, so this part of the Dockerfile will be
# cached (when building locally)
FROM pybase AS pybuild

# Install Python dependencies. They rarely change.
# For Docker images we install them to the local system, not to a virtualenv.
# Containers don't use pipenv.
COPY Pipfile Pipfile.lock /app/

# Need build-essential for:
# * google-re2
# * pysycopg2 (psycopg2-binary is evil because it links SSL -- as does Python)
# * PyICU
#
# Clean up after pipenv, because it leaves garbage in /root/.cache and
# /root/.local/share/virtualenvs, even when --deploy is used. (We test for
# presence of /root/.local/share/virtualenvs to decide whether we need a
# bind-mount in dev mode; so it can't exist in production.)
RUN true \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
      build-essential \
      libicu-dev \
      libpq-dev \
      libre2-dev \
      pkg-config \
      pybind11-dev \
    && pipenv install --dev --system --deploy \
    && rm -rf /root/.cache/pipenv /root/.local/share/virtualenvs \
    && apt-get remove --purge -y \
      build-essential \
      libicu-dev \
      libpq-dev \
      libre2-dev \
      pkg-config \
      pybind11-dev \
    && apt-get autoremove --purge -y \
    && rm -rf /var/lib/apt/lists/*

# Set up chroot-layers ASAP, so they're cached in a rarely-changing
# Docker layer.
COPY cjwkernel/setup-chroot-layers.sh /tmp/setup-chroot-layers.sh
RUN /tmp/setup-chroot-layers.sh && rm /tmp/setup-chroot-layers.sh
# Let chroots overlay the root FS -- meaning they must be on another FS.
# see cjwkernel/setup-sandboxes.sh
VOLUME /var/lib/cjwkernel/chroot


# 2. Node deps -- completely independent
# 2.1 jsbase: what we use in dev-in-docker
FROM node:12.14.1-buster-slim as jsbase

RUN mkdir /app
WORKDIR /app

# 2.2 jsbuild: where we build JavaScript assets
FROM jsbase AS jsbuild

COPY package.json package-lock.json babel.config.json /app/
RUN npm install

COPY webpack.config.js setupJest.js lingui.config.js /app/
COPY __mocks__/ /app/__mocks__/
COPY assets/ /app/assets/
# Inject unit tests into our continuous integration
# This catches mistakes that would otherwise foil us in bin/integration-test;
# and currently we rely on this line in our CI scripts (cloudbuild.yaml).
RUN npm test
RUN npm run lint
RUN node_modules/.bin/webpack --mode=production

# 3. Three prod servers will all be based on the same stuff:
FROM pybuild AS base

# Configure Black
COPY pyproject.toml pyproject.toml

COPY cjwkernel/ /app/cjwkernel/
COPY cjwstate/ /app/cjwstate/
COPY cjworkbench/ /app/cjworkbench/
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

# 3.1. assets: uploads assets to S3 (frontend will point end users there)
FROM base AS compile-assets
COPY staticfilesdev/ /app/staticfilesdev/
COPY assets/ /app/assets/
COPY --from=jsbuild /app/assets/bundles/ /app/assets/bundles/
RUN DJANGO_SETTINGS_MODULE=staticfilesdev.settings python ./manage.py collectstatic
RUN find /app/static -type f -printf "%s\t%P\n"

FROM amazon/aws-cli:2.1.30 AS upload-assets
COPY --from=compile-assets /app/static/ /app/static/
ENTRYPOINT []
# We use /bin/sh to substitute environment variables
CMD [ "/bin/sh", "-c", "exec aws s3 cp --recursive \"--endpoint-url=${AWS_S3_ENDPOINT:-https://s3.us-east-1.amazonaws.com}\" /app/static/ \"s3://${BUCKET_NAME:?must set BUCKET_NAME environment variable}/\"" ]

# 3.2. migrate: modifies database schema
FROM flyway/flyway:7.7.0-alpine AS migrate
COPY flyway/ /flyway/
CMD [ "migrate" ]

# 3.3. fetcher: runs fetch
FROM base AS fetcher
STOPSIGNAL SIGKILL
CMD [ "bin/fetcher-prod" ]

# 3.4. fetcher: runs fetch
FROM base AS renderer
STOPSIGNAL SIGKILL
CMD [ "bin/renderer-prod" ]

# 3.5. cron: schedules fetches and runs cleanup SQL
FROM base AS cron
STOPSIGNAL SIGKILL
CMD [ "bin/cron-prod" ]

# 3.6. frontend: serves website
FROM base AS frontend
# Add fake daphne, for unit tests running on google-cloud-build
COPY daphne/ /app/daphne/
COPY assets/icons/ /app/assets/icons/
COPY --from=jsbuild /app/assets/bundles/webpack-manifest.json /app/assets/bundles/webpack-manifest.json
# 8080 is Kubernetes' conventional web-server port
EXPOSE 8080
# Beware: uvicorn does not serve static files! Use upload-assets to push them
# to GCS and publish them there.
CMD [ "bin/frontend-prod", "8080" ]
