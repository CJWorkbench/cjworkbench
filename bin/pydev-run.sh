#!/bin/bash
#
# Run a command in the "pydev" environment.
#
# Usage: `bin/pydev.sh COMMAND ARGS...`
#
# For example: `bin/pydev.sh black cron/main.py`
#
# COMMAND is found in the pydev $PATH, starting with /opt/venv/django/bin/.
#
# /path/to/bin/pydev.sh will be mounted at /path/to/bin/pydev.sh _in the Docker
# container_. This is so commands like "black" can accept absolute paths or
# relative paths (relative to the current working directory, if it's within
# /path/to/).
#
# /tmp is also bind-mounted.

set -e

# Assumes we're in ~/src/cjworkbench/cjworkbench (and other plugins we may edit
# are in ~/src/cjworkbench/[pluginname]/
#
# So SRC=~/src/workbench -- `docker-run` will mount the _parent_ dir, which
# includes any plugin dir _and_ the `cjworkbench` repo.
SRC="$(realpath "$(dirname "$0")"/..)"

IMAGE=cjworkbench_pydev

do_create () {
  DOCKER_BUILDKIT=1 docker build "$SRC" --target=pydev --tag=$IMAGE
}

created_at_json=$(docker image inspect $IMAGE --format='{{json .Metadata.LastTagTime}}' | sed -e 's/"//g' 2>/dev/null || true)  # "" on not exists
if test -n "$created_at_json"; then
  created_at="$(date -u --iso-8601=seconds --date="$created_at_json")"
  want_created_after="$(stat "$SRC/venv" --format='@%Y' | date -u --iso-8601=seconds -f -)"
  if test "$created_at" "<" "$want_created_after"; then
    do_create
  fi
else
  do_create
fi

# We want to launch with the same filenames in the Docker container as outside
# it. That way, our text-editor plugins will be able to ask the LSP server
# about absolute paths.
WORKDIR="$PWD"

exec docker run --rm -i \
  --env LC_ALL=C.UTF-8 \
  --env LANG=C.UTF-8 \
  --env VIRTUAL_ENV=/opt/venv/django \
  --env PATH=/opt/venv/django/bin:/usr/local/bin:/usr/bin:/bin \
  --volume "$SRC":"$SRC":rw \
  --volume /tmp:/tmp:ro \
  --workdir "$WORKDIR" \
  "$IMAGE" \
  "$@"
