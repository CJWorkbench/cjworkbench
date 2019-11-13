#!/bin/sh

set -e

while ! curl --silent -I $MINIO_URL >/dev/null; do
  sleep 0.1
done

mc config host add workbench $MINIO_URL minio_root_access minio_root_secret
mc admin user add workbench $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
mc admin policy set workbench readwrite user=$MINIO_ACCESS_KEY

# Ignore "WARNING: failed to mount loopback filesystem" by redirecting
# stderr to /dev/null. (This hides other legit errors. If this laziness
# bit you ... sorry!)
cjwkernel/setup-sandboxes.sh all 2>/dev/null
exec pipenv run python ./manage.py test "$@"
