# 1. Python deps -- which rarely change, so this part of the Dockerfile will be
# cached (when building locally)
FROM python:3 AS pybuild

# We probably don't want these, long-term.
# nano: because we edit files on production
RUN apt-get update && apt-get install --no-install-recommends -y nano postgresql-client

RUN pip install pipenv

# Set up /app
RUN mkdir /app
WORKDIR /app

# Install Python dependencies. They rarely change.
# We install them to the local system, not to a virtualenv. That means in
# production, we don't use pipenv.
COPY Pipfile Pipfile.lock /app/
RUN pipenv install --dev --system --deploy

# nltk models (for sentiment)
RUN python -m nltk.downloader -d /usr/local/share/nltk_data vader_lexicon

# 2. Node deps -- completely independent
FROM node:10.1.0-slim AS jsbuild

RUN apt-get update && apt-get install --no-install-recommends -y git

RUN mkdir /app
WORKDIR /app

COPY package.json package-lock.json /app/
RUN npm install

COPY webpack.config.js setupJest.js /app/
COPY assets /app/assets/
# Inject unit tests into our continuous integration
# This is how Travis tests
RUN npm test
RUN node_modules/.bin/webpack -p


# 3. Complete app
FROM pybuild AS app

EXPOSE 8000

COPY --from=jsbuild /app/assets/ /app/assets/
COPY cjworkbench/ /app/cjworkbench/
COPY server/ /app/server/
COPY templates/ /app/templates/
COPY database.yml manage.py start-prod.sh /app/

# needed for django to load correctly
COPY --from=jsbuild /app/webpack-stats.json /app/webpack-stats.json

# Inject unit tests into our continuous integration
# This is how Travis tests
RUN ./manage.py test

CMD [ "./start-prod.sh" ]
