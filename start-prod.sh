#!/bin/bash

# Run the Workbench server in production configuration
# Expects the database up, e.g. docker-compose -f database.yml up -d

# Production env vars. Must set CJW_SECRET_KEY externally!
export CJW_PRODUCTION=True
export CJW_ALLOWED_HOST=*
export CJW_DB_PASSWORD=cjworkbench

python manage.py runserver --insecure 2>&1
