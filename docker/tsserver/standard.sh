#!/bin/bash

set -e

IMAGE=$(docker build -q "$(dirname "$0")")

# Assumes we're in ~/src/cjworkbench/cjworkbench (and other plugins we may edit
# are in ~/src/cjworkbench/[pluginname]/
SRC="$(realpath ~/src/cjworkbench)"

# We want to launch with the same filenames in the Docker container as outside
# it. That way, our text-editor plugins will be able to ask the LSP server
# about absolute paths.
WORKDIR="$PWD"

exec docker run --rm -i \
  --env LC_ALL=C.UTF-8 \
  --env LANG=C.UTF-8 \
  --volume cjworkbench_node_modules:"$SRC"/cjworkbench/node_modules/:ro \
  --workdir "$WORKDIR" \
  "$IMAGE" \
  "$SRC"/cjworkbench/node_modules/.bin/standard --fix --stdin "$@"
