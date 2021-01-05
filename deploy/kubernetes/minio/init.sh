#!/bin/bash

set -ex

DIR="$(dirname "$0")"
ENV=${1:?"Usage: $0 ENVIRONMENT"}
CLUSTER_NAME="workbench"
if [ "$ENV" = "production" ]; then
  DOMAIN_NAME="workbenchdata.com"
  PROJECT_NAME="workbenchdata-production"
else
  DOMAIN_NAME="workbenchdata-staging.com"
  PROJECT_NAME="workbench-staging"
fi

# We give minio, migrate, renderer and fetcher direct access to Google Cloud
# Storage using its interoperability ("S3") API. The `cjwstate.minio` module
# accesses GCS using botocore and boto3, as though it were S3.
#
# frontend doesn't: user uploads need AWS IAM STS tokens. S3 handles big
# upload through STS tokens and multipart uploads; GCS handles big upload
# through resumable uploads. frontend -- and indeed, the end-user -- must
# use minio to emulate S3, because GCS doesn't emulate its STS tokens.
#
# On production, we only use minio for user file uploads. All this madness is
# only for user file uploads. AAAAAH.
for sa in minio migrate-sa renderer-sa fetcher-sa; do
  kubectl create secret generic gcs-s3-$sa-credentials --from-env-file <(
    gsutil hmac create \
      -p $PROJECT_NAME \
      $CLUSTER_NAME-$sa@$PROJECT_NAME.iam.gserviceaccount.com \
      | sed -e 's/Access ID: */AWS_ACCESS_KEY_ID=/' -e 's/Secret: */AWS_SECRET_ACCESS_KEY=/'
  )
done
# migrate-sa can do anything
gcloud projects add-iam-policy-binding $PROJECT_NAME \
  --member=serviceAccount:$CLUSTER_NAME-migrate-sa@$PROJECT_NAME.iam.gserviceaccount.com \
  --role=roles/storage.admin

# renderer, frontend, fetcher and tusd are more restricted.
# [2020-12-16] frontend doesn't use GCS directly: it goes through minio. But
# we're writing these policies as documentation.

# stored-objects: fetcher+frontend write; renderer reads
gsutil iam ch \
  serviceAccount:$CLUSTER_NAME-fetcher-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-frontend-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-renderer-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
  gs://stored-objects.$DOMAIN_NAME
# user-files: frontend writes; fetcher+renderer read
gsutil iam ch \
  serviceAccount:$CLUSTER_NAME-fetcher-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
  serviceAccount:$CLUSTER_NAME-frontend-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-renderer-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
  gs://user-files.$DOMAIN_NAME
# external-modules: frontend writes; fetcher+renderer read
gsutil iam ch \
  serviceAccount:$CLUSTER_NAME-fetcher-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
  serviceAccount:$CLUSTER_NAME-frontend-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-renderer-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
  gs://external-modules.$DOMAIN_NAME
# cached-render-results: frontend+renderer write; frontend can read (for an edge case)
gsutil iam ch \
  serviceAccount:$CLUSTER_NAME-fetcher-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
  serviceAccount:$CLUSTER_NAME-frontend-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-renderer-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  gs://cached-render-results.$DOMAIN_NAME
# upload: tusd writes; frontend reads and writes (when deleting upon completed upload)
gsutil iam ch \
  serviceAccount:$CLUSTER_NAME-tusd-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-frontend-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  gs://upload.$DOMAIN_NAME


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

sleep 60
kubectl set env statefulset/minio-etcd ETCD_INITIAL_CLUSTER_STATE=existing

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
  --image=minio/mc:RELEASE.2020-10-03T02-54-56Z \
  --overrides='
    {
      "spec": {
        "containers": [{
          "name": "minio-adduser",
          "image": "minio/mc:RELEASE.2020-10-03T02-54-56Z",
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
gcloud dns record-sets transaction add --zone=workbench-zone --name user-files.$DOMAIN_NAME. --ttl 7200 --type A $STATIC_IP
gcloud dns record-sets transaction execute --zone=workbench-zone
