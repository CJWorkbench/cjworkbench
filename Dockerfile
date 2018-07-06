# 1. Python deps -- which rarely change, so this part of the Dockerfile will be
# cached (when building locally)
FROM python:3.6.6-slim-stretch AS pybuild

# We probably don't want these, long-term.
# nano: because we edit files on production
# postgresql-client: because we poll the DB on prod before ./manage.py migrate
RUN mkdir -p /usr/share/man/man1 /usr/share/man/man7 \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        git \
        nano \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*


RUN pip install pipenv

# Set up /app
RUN mkdir /app
WORKDIR /app

# Install Python dependencies. They rarely change.
# We install them to the local system, not to a virtualenv. That means in
# production, we don't use pipenv.
COPY Pipfile Pipfile.lock /app/
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
      build-essential \
      libpq-dev \
    && pipenv install --dev --system --deploy \
    && apt-get remove --purge -y \
      libpq-dev \
      build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# nltk models (for sentiment)
RUN python -m nltk.downloader -d /usr/local/share/nltk_data vader_lexicon


# 1.1 integration-test deps
# Depends on pybuild because integration tests run Django shell to fiddle
# with database.
FROM pybuild AS integration-test-deps

RUN pip install capybara-py selenium
# Install Firefox deps (and curl and xvfb). Debian Stretch has Firefox v52,
# which is way too old; but we'll install 52's dependencies and hope they
# satisfy Firefox v61
RUN apt-get update \
    && bash -c 'apt-get install -y --no-install-recommends $(apt-cache depends firefox-esr | awk "/Depends:/{print\$2}")' \
    && apt-get install --no-install-recommends -y \
        curl \
        xauth \
        xvfb \
        bzip2 \
    && rm -rf /var/lib/apt/lists/*
RUN curl -L https://download-installer.cdn.mozilla.net/pub/firefox/releases/61.0/linux-x86_64/en-US/firefox-61.0.tar.bz2 \
        | tar jx -C /opt \
        && ln -s /opt/firefox/firefox /usr/bin/firefox
RUN curl -L https://github.com/mozilla/geckodriver/releases/download/v0.21.0/geckodriver-v0.21.0-linux64.tar.gz \
        | tar zx -C /usr/bin/ \
        && chmod +x /usr/bin/geckodriver


# 2. Node deps -- completely independent
FROM node:10.1.0-slim AS jsbuild

RUN mkdir /app
WORKDIR /app

COPY package.json package-lock.json /app/
RUN npm install

COPY webpack.config.js setupJest.js /app/
COPY __mocks__/ /app/__mocks__/
COPY assets/ /app/assets/
# Inject unit tests into our continuous integration
# This is how Travis tests
RUN npm test
RUN node_modules/.bin/webpack -p


# 3. Three prod servers will all be based on the same stuff:
FROM pybuild AS base

# assets/ is static files. TODO nix them here; host them elsewhere
COPY assets/ /app/assets/
COPY --from=jsbuild /app/assets/bundles/ /app/assets/bundles/
COPY --from=jsbuild /app/webpack-stats.json /app/
COPY cjworkbench/ /app/cjworkbench/
COPY server/ /app/server/
COPY bin/ /app/bin/
COPY templates/ /app/templates/
COPY manage.py /app/
# Inject unit tests into our continuous integration
# This is how Travis tests
RUN ./manage.py test -v2

# 3.1. migrate: runs ./manage.py migrate
FROM base AS migrate
CMD [ "bin/migrate-prod" ]

# 3.2. backend: runs background tasks
FROM base AS backend
CMD [ "./manage.py", "run-background-loop" ]

# 3.3. frontend: serves website
FROM base AS frontend
# 8080 is Kubernetes' conventional web-server port
EXPOSE 8080
# TODO nix --insecure; serve static files elsewhere
CMD [ "./manage.py", "runserver", "--insecure", "0.0.0.0:8080" ]

# 4. integration-test: tests all the above
FROM integration-test-deps AS integration-test
WORKDIR /app
COPY cjworkbench/ /app/cjworkbench/
COPY server/ /app/server/
COPY integrationtests/ /app/integrationtests/
CMD [ "sh", "-c", "xvfb-run -a -s '-screen 0 1200x768x24' python -m unittest discover -v integrationtests" ]
