# 1.1 integration-test deps
# Depends on pybuild because integration tests run Django shell to fiddle
# with database.
FROM python:3.7.2-slim-stretch AS deps

# Install Firefox deps (and curl, xvfb, vnc). Debian Stretch has Firefox v52,
# which is way too old; but we'll install 52's dependencies and hope they
# satisfy Firefox v63
RUN apt-get update \
    && bash -c 'apt-get install -y --no-install-recommends $(apt-cache depends firefox-esr | awk "/Depends:/{print\$2}")' \
    && apt-get install --no-install-recommends -y \
        curl \
        xauth \
        xvfb \
        tigervnc-standalone-server \
        bzip2 \
    && rm -rf /var/lib/apt/lists/*

# Install Firefox. It's a separate step so it's easier to resume docker build.
RUN curl -L https://download-installer.cdn.mozilla.net/pub/firefox/releases/67.0/linux-x86_64/en-US/firefox-67.0.tar.bz2 \
        | tar jx -C /opt \
        && ln -s /opt/firefox/firefox /usr/bin/firefox

# Install geckodriver. It's a separate step so it's easier to resume docker build.
RUN curl -L https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz \
        | tar zx -C /usr/bin/ \
        && chmod +x /usr/bin/geckodriver

# Install the Python deps we use for integration tests.
#
# Integration tests don't rely on the Django stack, and that makes this
# Dockerfile compile faster and cache better.
RUN pip install psycopg2-binary capybara-py selenium minio

WORKDIR /app


FROM deps AS dev
# We're a VNC server
EXPOSE 5901
# The developer can edit tests and re-run them quickly
# /app/integrationtests is a volume in dev, a COPY in cloudbuild
VOLUME /app/integrationtests
CMD [ "sh", "-c", "xvfb-run -a -s '-screen 0 1200x768x24' python -m unittest discover -v integrationtests -f" ]

FROM deps AS cloudbuild
# /app/integrationtests is a volume in dev, a COPY in cloudbuild
COPY integrationtests/ /app/integrationtests/
CMD [ "sh", "-c", "until curl --output /dev/null http://frontend:8080 --silent --head --fail; do sleep 1; done; xvfb-run -a -s '-screen 0 1200x768x24' python -m unittest discover -v integrationtests -f" ]
