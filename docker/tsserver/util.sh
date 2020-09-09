#!/bin/bash

set -e

IMAGE=$(DOCKER_BUILDKIT=1 docker build -q "$(dirname "$0")")

# Assumes we're in ~/src/cjworkbench/cjworkbench (and other plugins we may edit
# are in ~/src/cjworkbench/[pluginname]/
#
# So SRC=~/src/workbench -- `docker-run` will mount the _parent_ dir, which
# includes any plugin dir _and_ the `cjworkbench` repo.
SRC="$(realpath "$(dirname "$0")"/../../..)"

# We want to launch with the same filenames in the Docker container as outside
# it. That way, our text-editor plugins will be able to ask the LSP server
# about absolute paths.
WORKDIR="$PWD"

start_docker_container() {
  docker run \
    --detach \
    --rm \
    --name cjworkbench_tsserver \
    --volume "$SRC":"$SRC":rw \
    --volume cjworkbench_node_modules:"$SRC"/cjworkbench/node_modules/:rw \
    "$IMAGE" \
    sleep 999999
  sleep 1  # wait to make sure it's started
}

exec_docker_run() {
  container=$(docker container ls -q --filter name=cjworkbench_tsserver)
  if [ "$container" = "" ]; then
    container=$(start_docker_container)
  fi

  docker exec \
    -i \
    --env LC_ALL=C.UTF-8 \
    --env LANG=C.UTF-8 \
    --env PATH="/usr/local/bin:/usr/bin:/bin:"$SRC"/cjworkbench/node_modules/.bin" \
    --workdir "$WORKDIR" \
    cjworkbench_tsserver \
    "$@"
}
