#!/bin/bash

set -e

# Run the Workbench server in production configuration
# Expects the database up, e.g. docker-compose -f database.yml up -d

# Production env vars. Must set CJW_SECRET_KEY externally!
export CJW_PRODUCTION=True
export CJW_DB_HOST=workbench-db
export CJW_DB_PASSWORD=cjworkbench

# required or we won't get any logs when running in docker container
export PYTHONUNBUFFERED=0

# for some reason this seems to fail in the Dockerfile, so do it here
cron

# Sleep until Postgres is available. Otherwise, manage.py will crash.
until PGPASSWORD="$CJW_DB_PASSWORD" psql -q --host="$CJW_DB_HOST" --username=cjworkbench cjworkbench -c 'SELECT 1' >/dev/null; do
	echo "Postgres database $CJW_DB_HOST/cjworkbench not yet available. Will retry in 1s." >&2
	sleep 1
done

./manage.py migrate sites
./manage.py migrate
./manage.py load_socialaccounts
./manage.py reload-internal-modules

./manage.py runserver --insecure 0.0.0.0:8000
