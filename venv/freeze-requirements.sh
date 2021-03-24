#!/bin/sh

cd "$(dirname "$0")"

# Tag the image, so we cache all interim steps
DOCKER_BUILDKIT=1 docker build . --tag=cjworkbench-freeze-requirements-txt

for venv in django cjwkernel; do
  name="$venv-requirements-frozen.txt"
  docker run -it --rm cjworkbench-freeze-requirements-txt cat $name > $name
done
