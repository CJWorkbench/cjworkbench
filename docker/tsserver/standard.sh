#!/bin/bash

. "$(dirname "$0")"/util.sh

exec_docker_run "$SRC"/cjworkbench/node_modules/.bin/standard "$@"
