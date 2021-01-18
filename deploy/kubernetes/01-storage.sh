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

gsutil mb gs://user-files.$DOMAIN_NAME
gsutil mb gs://static.$DOMAIN_NAME
gsutil mb gs://stored-objects.$DOMAIN_NAME
gsutil mb gs://external-modules.$DOMAIN_NAME
gsutil mb gs://cached-render-results.$DOMAIN_NAME
gsutil mb gs://upload.$DOMAIN_NAME
gsutil ubla set on gs://user-files.$DOMAIN_NAME
gsutil ubla set on gs://static.$DOMAIN_NAME
gsutil ubla set on gs://stored-objects.$DOMAIN_NAME
gsutil ubla set on gs://external-modules.$DOMAIN_NAME
gsutil ubla set on gs://cached-render-results.$DOMAIN_NAME
gsutil ubla set on gs://upload.$DOMAIN_NAME

gcloud iam service-accounts keys create application_default_credentials.json \
  --iam-account $CLUSTER_NAME-tusd@$PROJECT_NAME.iam.gserviceaccount.com
kubectl create secret generic tusd-gcs-credentials \
  --from-file=./application_default_credentials.json
rm application_default_credentials.json

# Uploads expire after 1d
echo '{"lifecycle":{"rule":[{"action":{"type":"Delete"},"condition":{"age":1}}]}}' \
  > 1d-lifecycle.json
gsutil lifecycle set 1d-lifecycle.json gs://upload.$DOMAIN_NAME
rm 1d-lifecycle.json

# We give cron, migrate, renderer and fetcher direct access to Google Cloud
# Storage using its interoperability ("S3") API. The `cjwstate.s3` module
# uses this.
for sa in cron-sa migrate-sa renderer-sa fetcher-sa; do
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

# cron-sa, renderer-sa, frontend-sa, fetcher-sa and tusd-sa are more restricted.

# stored-objects: cron deletes; fetcher+frontend write; renderer reads
gsutil iam ch \
  serviceAccount:$CLUSTER_NAME-cron-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-fetcher-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-frontend-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-renderer-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
  gs://stored-objects.$DOMAIN_NAME
# user-files: cron deletes; frontend writes; fetcher+renderer read
gsutil iam ch \
  serviceAccount:$CLUSTER_NAME-cron-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
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
# cached-render-results: cron deletes; frontend+renderer write; fetcher can read
# (Fetcher reads because fetches can depend on prior results -- a bizarre feature.)
gsutil iam ch \
  serviceAccount:$CLUSTER_NAME-cron-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
  serviceAccount:$CLUSTER_NAME-fetcher-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectViewer \
  serviceAccount:$CLUSTER_NAME-frontend-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-renderer-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  gs://cached-render-results.$DOMAIN_NAME
# upload: tusd writes; frontend reads and writes (when deleting upon completed upload)
gsutil iam ch \
  serviceAccount:$CLUSTER_NAME-tusd-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  serviceAccount:$CLUSTER_NAME-frontend-sa@$PROJECT_NAME.iam.gserviceaccount.com:objectAdmin \
  gs://upload.$DOMAIN_NAME


# Set up load balancer
gcloud compute addresses create user-files --global

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
