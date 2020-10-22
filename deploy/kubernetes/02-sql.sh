#!/bin/sh

set -e
set -x

CLUSTER_NAME="workbench"
ENV="$1"
if [ "$ENV" = "production" ]; then
  DB_INSTANCE_RESOURCES="--cpu=2 --memory=5GB --storage-size=10"
  PROJECT_NAME="workbenchdata-production"  # workbench-production was taken
else
  DB_INSTANCE_RESOURCES="--tier db-g1-small --storage-size=10"
  PROJECT_NAME="workbench-staging"
fi

# Add VPC peering between project's network and Google's Cloud SQL network
# https://cloud.google.com/sql/docs/postgres/configure-private-services-access
gcloud compute addresses create google-managed-services-default \
  --project="$PROJECT_NAME" \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=24 \
  --network=default

gcloud services vpc-peerings connect \
  --project="$PROJECT_NAME" \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-default \
  --network=default \

# Actually create the Postgres cloud-SQL instance
gcloud beta sql instances create postgres \
  --project="$PROJECT_NAME" \
  --database-version=POSTGRES_12 \
  $DB_INSTANCE_RESOURCES \
  --zone=us-central1-b \
  --network=default \
  --no-assign-ip \
  --backup-start-time=00:00 \
  --require-ssl

# For now, every service connects as the one "cjworkbench" user
# TODO access control
PASSWORD="$(openssl rand -base64 20)"
kubectl create secret generic postgres-cjworkbench-credentials \
  --from-literal=username=cjworkbench \
  --from-literal=database=cjworkbench \
  --from-literal=password="$PASSWORD"
gcloud sql users create cjworkbench \
  --project="$PROJECT_NAME" \
  --instance=postgres \
  --password="$PASSWORD"
