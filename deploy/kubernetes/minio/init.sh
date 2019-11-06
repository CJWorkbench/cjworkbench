#!/bin/bash

set -ex

DIR="$(dirname "$0")"
ENV=${1:?"Usage: $0 ENVIRONMENT"}

# Generate new root key+certificate. (We'll delete the key forever -- it has no
# long-term value.)
openssl req \
  -nodes \
  -sha256 \
  -x509 \
  -days 99999 \
  -newkey rsa:2048 \
  -keyout ca.key \
  -out ca.crt \
  -subj "/CN=ca.minio-etcd.$ENV.cluster.local"

for name in minio-etcd-0 minio-etcd-1 minio-etcd-2; do
  # Generate a peer keys+certificates signed by ca.crt
  openssl req \
    -nodes \
    -sha256 \
    -newkey rsa:2048 \
    -days 99999 \
    -keyout $name-peer.key \
    -out $name-peer.csr \
    -subj "/CN=$name.minio-etcd-peer.$ENV.svc.cluster.local"

  openssl x509 \
    -sha256 \
    -req -in $name-peer.csr \
    -days 99999 \
    -CA ca.crt \
    -CAkey ca.key \
    -CAcreateserial \
    -out $name-peer.crt
done

# Generate server certificate, which points to service name
openssl req \
  -nodes \
  -sha256 \
  -newkey rsa:2048 \
  -keyout server.key \
  -out server.csr \
  -days 99999 \
  -subj "/CN=minio-etcd.$ENV.svc.cluster.local"

openssl x509 \
  -req -in server.csr \
  -sha256 \
  -CA ca.crt \
  -CAkey ca.key \
  -CAcreateserial \
  -days 99999 \
  -out server.crt

# Generate client certificate -- one that etcd is happy with
# etcd likes to see "clientAuth" and doesn't care about DNS or IP addresses

openssl req \
  -nodes \
  -sha256 \
  -newkey rsa:2048 \
  -keyout client.key \
  -out client.csr \
  -days 99999 \
  -subj "/CN=client"

openssl x509 \
  -req -in client.csr \
  -sha256 \
  -CA ca.crt \
  -CAkey ca.key \
  -CAcreateserial \
  -days 99999 \
  -extensions client_server_ssl \
  -extfile <(printf "[client_server_ssl]\nextendedKeyUsage=clientAuth") \
  -out client.crt

kubectl -n $ENV create secret generic minio-etcd-server-certs \
  --from-file=ca.crt \
  --from-file=minio-etcd-0-peer.crt=minio-etcd-0-peer.crt \
  --from-file=minio-etcd-0-peer.key=minio-etcd-0-peer.key \
  --from-file=minio-etcd-1-peer.crt=minio-etcd-1-peer.crt \
  --from-file=minio-etcd-1-peer.key=minio-etcd-1-peer.key \
  --from-file=minio-etcd-2-peer.crt=minio-etcd-2-peer.crt \
  --from-file=minio-etcd-2-peer.key=minio-etcd-2-peer.key \
  --from-file=server.crt=server.crt \
  --from-file=server.key=server.key

kubectl -n $ENV create secret generic minio-etcd-client-certs \
  --from-file=ca.crt=ca.crt \
  --from-file=server.crt=server.crt \
  --from-file=client.crt=client.crt \
  --from-file=client.key=client.key

rm "$DIR"/*.{crt,csr,key,srl}

kubectl -n "$ENV" apply -f "$DIR"/minio-etcd-statefulset.yaml

# We'll use openssl rand to generate a password that only uses base64
# characters. Then we'll base64-encode it for use in kubectl commands.
kubectl -n "$ENV" create secret generic minio-access-key \
  --from-literal=access_key=$(openssl rand -base64 24 | base64) \
  --from-literal=secret_key=$(openssl rand -base64 24 | base64)

kubectl -n "$ENV" create secret generic minio-root-access-key \
  --from-literal=access_key=$(openssl rand -base64 24 | base64) \
  --from-literal=secret_key=$(openssl rand -base64 24 | base64)

kubectl -n "$ENV" apply -f "$DIR"/minio-deployment.yaml

# Now use the root user to generate the non-root user.
kubectl -n "$ENV" run minio-adduser \
  -i --rm=true \
  --restart=Never \
  --image=minio/mc:RELEASE.2019-10-09T22-54-57Z \
  --overrides='
    {
      "spec": {
        "containers": [{
          "name": "minio-adduser",
          "image": "minio/mc:RELEASE.2019-10-09T22-54-57Z",
          "command": [
            "sh", "-c",
            "while ! nc -z minio-service 80; do sleep 0.1; done; mc config host add workbench http://minio-service \"$ROOT_ACCESS_KEY\" \"$ROOT_SECRET_KEY\" && mc admin user add workbench \"$ACCESS_KEY\" \"$SECRET_KEY\" && mc admin policy set workbench readwrite user=\"$ACCESS_KEY\""
          ],
          "env": [
            {"name": "ROOT_ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "minio-root-access-key", "key": "access_key"}}},
            {"name": "ROOT_SECRET_KEY", "valueFrom": {"secretKeyRef": {"name": "minio-root-access-key", "key": "secret_key"}}},
            {"name": "ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "minio-access-key", "key": "access_key"}}},
            {"name": "SECRET_KEY", "valueFrom": {"secretKeyRef": {"name": "minio-access-key", "key": "secret_key"}}}
          ]
        }]
      }
    }'
