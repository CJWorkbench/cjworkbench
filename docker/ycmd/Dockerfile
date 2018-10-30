FROM debian:buster

RUN true \
    && apt-get update \
    && apt-get -y install curl gnupg \
    && curl -sSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - \
    && echo 'deb https://deb.nodesource.com/node_10.x buster main' | tee -a /etc/apt/sources.list \
    && apt-get update \
    && apt-get -y install \
      python3-pip \
      build-essential \
      cmake \
      python3-dev \
      nodejs \
      git \
    && pip3 install pipenv \
    && npm install -g typescript

RUN true \
    && mkdir -p /opt \
    && cd /opt \
    && git clone https://github.com/Valloric/ycmd \
    && cd /opt/ycmd \
    && git submodule update --init --recursive \
    && python3 build.py --clang-completer --ts-completer

# Entrypoint will be missing ycmd path: we'll write that in wrap-ycmd.sh
ENTRYPOINT [ "pipenv", "run", "python3" ]
