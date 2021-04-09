FROM python:3.8.8-slim-buster

# Need build-essential for:
# * pysycopg2 (binaries are evil because psycopg2 links SSL -- as does Python)
# * PyICU
#
# Need pkg-config to build PyICU
RUN mkdir -p /root/.local/share/virtualenvs \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
      build-essential \
      libicu-dev \
      libpq-dev \
      pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN python -mpip install pipdeptree

RUN mkdir /app
COPY ./ /app/
WORKDIR /app

RUN python -mvenv create django && \
  django/bin/python -m pip install -r django-toplevel-requirements.txt && \
  django/bin/python -m pip install --no-deps -r django-channels-requirements.txt && \
  django/bin/python /usr/local/lib/python3.8/site-packages/pipdeptree.py -f -e pipdeptree,pip,daphne \
    | tee django-requirements-frozen.txt

RUN python -mvenv create cjwkernel && \
  cjwkernel/bin/python -m pip install -r cjwkernel-toplevel-requirements.txt && \
  cjwkernel/bin/python /usr/local/lib/python3.8/site-packages/pipdeptree.py -f -e pipdeptree,pip \
    | tee cjwkernel-requirements-frozen.txt
