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
  --env VIRTUAL_ENV=/root/.local/share/virtualenvs/app-4PlAip0Q \
  --env PIPENV_MAX_DEPTH=10 \
  --volume cjworkbench_virtualenvs:/root/.local/share/virtualenvs/:rw \
  --volume "$SRC":"$SRC":rw \
  --workdir "$PWD" \
  "$IMAGE" \
  pipenv run pyls "$@"
