#!/bin/sh

set -e

DIR="$(realpath "$(dirname "$0")")"

docker build .
IMAGE=$(docker build -q .)

docker run \
  -it --rm \
  -v "$DIR"/allowed-syscalls.txt:/src/allowed-syscalls.txt \
  -v "$DIR"/rules.bpf:/src/rules.bpf \
  $IMAGE \
  ./compile-bpf allowed-syscalls.txt rules.bpf
