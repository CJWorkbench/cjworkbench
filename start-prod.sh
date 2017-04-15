#!/bin/bash

# Run the Workbench server in production configuration
# Expects the database up, e.g. docker-compose -f database.yml up -d

# Production env vars. Must set CJW_SECRET_KEY externally!
export CJW_PRODUCTION=True
export CJW_ALLOWED_HOST=*
export CJW_DB_PASSWORD=cjworkbench

# required or we won't get any logs when running in docker container
export PYTHONUNBUFFERED=0

python manage.py runserver --insecure
