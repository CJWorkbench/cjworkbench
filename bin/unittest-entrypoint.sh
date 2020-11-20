#!/bin/bash

set -e

setup_env() {
  # the /share subdir prevents spurious messages:
  # mc: Successfully created `/root/.mc/share`.
  # mc: Initialized share uploads `/root/.mc/share/uploads.json` file.
  # mc: Initialized share downloads `/root/.mc/share/downloads.json` file.
  mkdir -p /root/.mc/share
  echo '{"version":"10","aliases":{"workbench":{"url":"'$MINIO_URL'","accessKey":"minio_root_access","secretKey":"minio_root_secret","api":"s3v4","path":"auto"}}}' > /root/.mc/config.json

  while ! curl --silent --fail $MINIO_URL/minio/health/ready; do
    sleep 0.1
  done

  mc admin user add workbench $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
  mc admin policy set workbench readwrite user=$MINIO_ACCESS_KEY
}

# Skip setup_env if we are only testing within `cjwkernel/`.
#
# need_setup states:
# 0: "yes ... unless later, we only specify cjwkernel.*"
# 1: "no ... unless later, we add *not* cjwkernel.*"
# 2: "yes"
need_setup=0
for arg in "$@"; do
  case $arg in
    cjwkernel)
      # tests that don't require state
      if test $need_setup -eq 0; then
        need_setup=1
      fi
      ;;
    cjwkernel.*)
      # tests that don't require state
      if test $need_setup -eq 0; then
        need_setup=1
      fi
      ;;
    -*)
      # command-line flag passed to manage.py unittest
      ;;
    *)
      # tests that may require state
      need_setup=2
      break
      ;;
  esac
done
if test $need_setup -ne 1; then
  setup_env
fi

# Ignore "WARNING: failed to mount loopback filesystem" by redirecting
# stderr to /dev/null. (This hides other legit errors. If this laziness
# bit you ... sorry!)
cjwkernel/setup-sandboxes.sh all 2>/dev/null

exec pipenv run python ./manage.py test "$@"
