#!/bin/bash

# Run the Workbench server in production configuration
# Expects the database up, e.g. docker-compose -f database.yml up -d

# Production env vars. Must set CJW_SECRET_KEY externally!
export CJW_PRODUCTION=True
export CJW_DB_HOST=cjw-db  # name of docker-compose container
export CJW_DB_PASSWORD=cjworkbench

# required or we won't get any logs when running in docker container
export PYTHONUNBUFFERED=0

# for some reason this seems to fail in the Dockerfile, so do it here
service cron start

python manage.py migrate
python manage.py runserver --insecure 0.0.0.0:8000

