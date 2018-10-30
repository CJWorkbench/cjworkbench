#!/bin/bash

set -e

# YouCompleteMe tries to run "python /path/to/ycmd ...args".
# Make it exec "docker run ycmd ...args" -- that is, nix /path/to/ycmd.
if expr match "$1" ".*/ycmd$" >/dev/null; then
  shift >/dev/null
  set - "/opt/ycmd/ycmd" "$@"
fi

exec "$(dirname "$0")"/ycmd.sh "$@"
