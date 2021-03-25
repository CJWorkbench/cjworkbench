#!/bin/bash

. "$(dirname "$0")"/docker-run.sh

exec_docker_run /opt/venv/django/bin/black "$@"
