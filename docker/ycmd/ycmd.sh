#!/bin/bash

set -e

CWD="$(pwd)"

IMAGE=$(docker build -q "$(dirname "$0")")

SRC="$(realpath ~/src)"

find_port () {
    for arg in "$@"; do
        if [ "${arg:0:7}" = "--port=" ]; then
            echo "${arg:7}"
            return
        fi
    done
}

PORT="$(find_port "$@")"

PUBLISH_ARGS=""
HOST_ARGS=""
if [ -n "$PORT" ]; then
  PUBLISH_ARGS="--publish $PORT:$PORT"
  HOST_ARGS="--host 0.0.0.0"
fi

NVIM_SHARE="$(echo ~/.local/share/nvim)"

exec docker run --rm -i \
  --env LC_ALL=C.UTF-8 \
  --env LANG=C.UTF-8 \
  --volume "/tmp:/tmp:rw" \
  --volume "$NVIM_SHARE:$NVIM_SHARE:ro" \
  --volume cjworkbench_virtualenvs:/root/.local/share/virtualenvs/:rw \
  --volume "$SRC/:$SRC/:rw" \
  --volume cjworkbench_node_modules:"$SRC/cjworkbench/node_modules/:ro" \
  $PUBLISH_ARGS \
  --workdir "$CWD" \
  "$IMAGE" "$@" $HOST_ARGS
