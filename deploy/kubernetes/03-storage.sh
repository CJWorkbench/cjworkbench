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

# Uploads expire after 1d
echo '{"lifecycle":{"rule":[{"action":{"type":"Delete"},"condition":{"age":1}}]}}' \
  > 1d-lifecycle.json
gsutil lifecycle set 1d-lifecycle.json gs://upload.$DOMAIN_NAME
rm 1d-lifecycle.json

gcloud iam service-accounts create $CLUSTER_NAME-minio --display-name $CLUSTER_NAME-minio
# minio needs storage.buckets.list, or it prints lots of errors.
# (which seems like a bug.... https://github.com/minio/mc/issues/2652)
# Minio uses this permission to poll for bucket policies.
gcloud iam roles create Minio \
  --project=$PROJECT_NAME \
  --permissions=storage.buckets.list,storage.buckets.get,storage.objects.create,storage.objects.delete,storage.objects.get,storage.objects.list,storage.objects.update
gcloud projects add-iam-policy-binding $PROJECT_NAME \
  --member=serviceAccount:$CLUSTER_NAME-minio@$PROJECT_NAME.iam.gserviceaccount.com \
  --role=roles/storage.admin

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


# We'll use openssl rand to generate a password that only uses base64
# characters. Then we'll base64-encode it for use in kubectl commands.
kubectl create secret generic minio-access-key \
  --from-literal=access_key=$(openssl rand -base64 24 | base64) \
  --from-literal=secret_key=$(openssl rand -base64 24 | base64)

# Set up load balancer
kubectl apply -f "$DIR"/minio-service.yaml
gcloud compute addresses create user-files --global
kubectl apply -f "$DIR"/minio-$ENV-ingress.yaml

# Set up DNS
STATIC_IP=$(gcloud compute addresses describe user-files --global | grep address: | cut -b10-)
gcloud dns record-sets transaction start --zone=workbench-zone
gcloud dns record-sets transaction add --zone=workbench-zone --name user-files.$DOMAIN_NAME. --ttl 7200 --type A $STATIC_IP
gcloud dns record-sets transaction execute --zone=workbench-zone

gsutil iam ch allUsers:objectViewer gs://static.$DOMAIN_NAME
echo '[{"origin":"*","method":"GET","maxAgeSeconds":3000}]' > static-cors.json \
  && gsutil cors set static-cors.json gs://static.$DOMAIN_NAME \
  && rm -f static-cors.json
gcloud dns record-sets transaction start --zone=$ZONE_NAME
gcloud dns record-sets transaction add --zone $ZONE_NAME --name static.$DOMAIN_NAME. --ttl 7200 --type CNAME c.storage.googleapis.com.
gcloud dns record-sets transaction execute --zone $ZONE_NAME
