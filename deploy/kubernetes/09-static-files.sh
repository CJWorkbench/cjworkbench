#!/bin/bash

ENV="production"  # "staging" or "production"
CLUSTER_NAME="workbench"
if [ "$ENV" = "staging" ]; then
  DOMAIN_NAME="workbenchdata-staging.com"
  PROJECT_NAME="workbench-staging"
else
  DOMAIN_NAME="workbenchdata.com"
  PROJECT_NAME="workbenchdata-production"  # workbench-production was taken
fi
ZONE_NAME="workbench-zone"

set -x -e

# Enable CORS. Anyone can download these files.
echo '[{"origin":"*","method":"GET","maxAgeSeconds":3000}]' > static-cors.json \
  && gsutil cors set static-cors.json gs://static.$DOMAIN_NAME \
  && rm -f static-cors.json

# Set up an HTTPS load balancer to serve the bucket.
# ref: https://cloud.google.com/cdn/docs/setting-up-cdn-with-bucket#gcloud
gcloud compute addresses create static-files-ip --global
STATIC_FILES_IP=$(gcloud compute addresses describe static-files-ip --format="get(address)" --global)

gcloud dns record-sets transaction start --zone=$ZONE_NAME
gcloud dns record-sets transaction add --zone=$ZONE_NAME --name static.$DOMAIN_NAME. --ttl 300 --type A $STATIC_FILES_IP
gcloud dns record-sets transaction execute --zone=$ZONE_NAME

gcloud compute backend-buckets create static-backend-bucket \
  --gcs-bucket-name=static.$DOMAIN_NAME \
  --enable-cdn

gcloud compute url-maps create static-lb \
  --default-backend-bucket=static-backend-bucket

gcloud compute ssl-certificates create static-cert \
  --description="static.$DOMAIN_NAME" \
  --domains="static.$DOMAIN_NAME" \
  --global

gcloud compute target-https-proxies create static-lb-proxy \
  --url-map=static-lb \
  --ssl-certificates=static-cert \
  --global-ssl-certificates

gcloud compute forwarding-rules create static-lb-forwarding-rule \
  --address=static-files-ip \
  --global \
  --target-https-proxy=static-lb-proxy \
  --ports=443
