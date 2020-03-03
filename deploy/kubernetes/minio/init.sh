#!/bin/bash

set -ex

DIR="$(dirname "$0")"
ENV=${1:?"Usage: $0 ENVIRONMENT"}
if [ "$ENV" = "production" ]; then
  DOMAIN="workbenchdata.com"
else
  DOMAIN="workbenchdata-staging.com"
fi

# Generate new root key+certificate. (We'll delete the key forever -- it has no
# long-term value.)
openssl req \
  -nodes \
  -sha256 \
  -x509 \
  -days 99999 \
  -newkey rsa:2048 \
  -keyout "$DIR"/ca.key \
  -out "$DIR"/ca.crt \
  -subj "/CN=ca.minio-etcd.default.cluster.local"

for name in minio-etcd-0 minio-etcd-1 minio-etcd-2; do
  # Generate a peer keys+certificates signed by ca.crt
  openssl req \
    -nodes \
    -sha256 \
    -newkey rsa:2048 \
    -days 99999 \
    -keyout "$DIR"/$name-peer.key \
    -out "$DIR"/$name-peer.csr \
    -subj "/CN=$name.minio-etcd-peer.default.svc.cluster.local"

  openssl x509 \
    -sha256 \
    -req -in "$DIR"/$name-peer.csr \
    -days 99999 \
    -CA "$DIR"/ca.crt \
    -CAkey "$DIR"/ca.key \
    -CAcreateserial \
    -out "$DIR"/$name-peer.crt
done

# Generate server certificate, which points to service name
openssl req \
  -nodes \
  -sha256 \
  -newkey rsa:2048 \
  -keyout "$DIR"/server.key \
  -out "$DIR"/server.csr \
  -days 99999 \
  -subj "/CN=minio-etcd.default.svc.cluster.local"

openssl x509 \
  -req -in "$DIR"/server.csr \
  -sha256 \
  -CA "$DIR"/ca.crt \
  -CAkey "$DIR"/ca.key \
  -CAcreateserial \
  -days 99999 \
  -out "$DIR"/server.crt

# Generate client certificate -- one that etcd is happy with
# etcd likes to see "clientAuth" and doesn't care about DNS or IP addresses

openssl req \
  -nodes \
  -sha256 \
  -newkey rsa:2048 \
  -keyout "$DIR"/client.key \
  -out "$DIR"/client.csr \
  -days 99999 \
  -subj "/CN=client"

openssl x509 \
  -req -in "$DIR"/client.csr \
  -sha256 \
  -CA "$DIR"/ca.crt \
  -CAkey "$DIR"/ca.key \
  -CAcreateserial \
  -days 99999 \
  -extensions client_server_ssl \
  -extfile <(printf "[client_server_ssl]\nextendedKeyUsage=clientAuth") \
  -out "$DIR"/client.crt

kubectl create secret generic minio-etcd-server-certs \
  --from-file="$DIR"/ca.crt \
  --from-file=minio-etcd-0-peer.crt="$DIR"/minio-etcd-0-peer.crt \
  --from-file=minio-etcd-0-peer.key="$DIR"/minio-etcd-0-peer.key \
  --from-file=minio-etcd-1-peer.crt="$DIR"/minio-etcd-1-peer.crt \
  --from-file=minio-etcd-1-peer.key="$DIR"/minio-etcd-1-peer.key \
  --from-file=minio-etcd-2-peer.crt="$DIR"/minio-etcd-2-peer.crt \
  --from-file=minio-etcd-2-peer.key="$DIR"/minio-etcd-2-peer.key \
  --from-file=server.crt="$DIR"/server.crt \
  --from-file=server.key="$DIR"/server.key

kubectl create secret generic minio-etcd-client-certs \
  --from-file=ca.crt="$DIR"/ca.crt \
  --from-file=server.crt="$DIR"/server.crt \
  --from-file=client.crt="$DIR"/client.crt \
  --from-file=client.key="$DIR"/client.key

rm "$DIR"/*.{crt,csr,key,srl}

kubectl apply -f "$DIR"/minio-etcd-statefulset.yaml

# We'll use openssl rand to generate a password that only uses base64
# characters. Then we'll base64-encode it for use in kubectl commands.
kubectl create secret generic minio-access-key \
  --from-literal=access_key=$(openssl rand -base64 24 | base64) \
  --from-literal=secret_key=$(openssl rand -base64 24 | base64)

kubectl create secret generic minio-root-access-key \
  --from-literal=access_key=$(openssl rand -base64 24 | base64) \
  --from-literal=secret_key=$(openssl rand -base64 24 | base64)

kubectl apply -f "$DIR"/minio-deployment.yaml
kubectl apply -f "$DIR"/minio-service.yaml

# Now use the root user to generate the non-root user.
kubectl run minio-adduser \
  -i --rm=true \
  --restart=Never \
  --image=minio/mc:RELEASE.2020-02-25T18-10-03Z \
  --overrides='
    {
      "spec": {
        "containers": [{
          "name": "minio-adduser",
          "image": "minio/mc:RELEASE.2020-02-25T18-10-03Z",
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

# Set up load balancer
kubectl apply -f "$DIR"/minio-service.yaml
gcloud compute addresses create user-files --global
kubectl apply -f "$DIR"/minio-$ENV-ingress.yaml

# Set up DNS
STATIC_IP=$(gcloud compute addresses describe user-files --global | grep address: | cut -b10-)
gcloud dns record-sets transaction start --zone=workbench-zone
gcloud dns record-sets transaction add --zone=workbench-zone --name user-files.$DOMAIN. --ttl 7200 --type A $STATIC_IP
gcloud dns record-sets transaction execute --zone=workbench-zone
