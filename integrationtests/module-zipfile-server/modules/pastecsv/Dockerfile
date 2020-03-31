# We run everything in a Dockerfile so we can pull arrow-tools binaries
FROM workbenchdata/arrow-tools:v0.0.11 as arrow-tools
FROM python:3.8.1-buster AS test

COPY --from=arrow-tools /usr/bin/csv-to-arrow /usr/bin/csv-to-arrow

RUN pip install black pyflakes isort pytest

WORKDIR /app
COPY setup.py /app/
RUN pip install .[tests]

COPY . /app/

RUN true \
      && pyflakes . \
      && black --check . \
      && isort --check --recursive . \
      && pytest --verbose
