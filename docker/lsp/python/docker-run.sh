#!/bin/bash

set -e

# Assumes we're in ~/src/cjworkbench/cjworkbench (and other plugins we may edit
# are in ~/src/cjworkbench/[pluginname]/
#
# So SRC=~/src/workbench -- `docker-run` will mount the _parent_ dir, which
# includes any plugin dir _and_ the `cjworkbench` repo.
SRC="$(realpath "$(dirname "$0")"/../../..)"

IMAGE=$(DOCKER_BUILDKIT=1 docker build -q "$SRC" --target=pydev)

# We want to launch with the same filenames in the Docker container as outside
# it. That way, our text-editor plugins will be able to ask the LSP server
# about absolute paths.
WORKDIR="$PWD"

exec_docker_run() {
  exec docker run --rm -i \
    --env LC_ALL=C.UTF-8 \
    --env LANG=C.UTF-8 \
    --env VIRTUAL_ENV=/opt/venv/django \
    --volume "$SRC":"$SRC":rw \
    --workdir "$WORKDIR" \
    "$IMAGE" \
    "$@"
}
