#!/bin/bash

set -e
set -x

cd "$(dirname "$0")"

rm -f ./*.{srl,csr,key,crt}

# root-CA ("Certificate authority") key
openssl genrsa -out ca.key 2048
# root-CA certificate (server and client will trust this)
openssl req -x509 -new -key ca.key -sha256 -days 9999 -out ca.crt -subj '/CN=localhost'

# server key
openssl genrsa -out server.key 2048
# server CSR (certificate signing request)
openssl req -new -key server.key -subj '/CN=localhost' -out server.csr
# server certificate (signed by root CA)
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 9999 -sha256

# Build "server-chain.crt"
cat server.crt ca.crt > server-chain.crt

# Nix unused files
rm -f ca.{srl,key} server.{csr,crt}

# certificates must be readable in Docker container
chmod 0644 ca.crt server.key server-chain.crt
