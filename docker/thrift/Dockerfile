# Need thrift==0.13.0
# https://packages.debian.org/sid/thrift-compiler
FROM debian:sid-slim

RUN true \
      && apt-get update \
      && apt-get install --no-install-recommends -y \
          thrift-compiler \
      && rm -rf /var/lib/apt/lists/*
