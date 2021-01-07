#!/bin/bash

ENV="production"  # or "production", or....
CLUSTER_NAME="workbench"
if [ "$ENV" = "staging" ]; then
  DOMAIN_NAME="workbenchdata-staging.com"
  PROJECT_NAME="workbench-staging"
else
  DOMAIN_NAME="workbenchdata.com"
  PROJECT_NAME="workbenchdata-production"  # workbench-production was taken
fi
ZONE_NAME="workbench-zone"

gcloud compute addresses create tusd-ip --global
STATIC_IP=$(gcloud compute addresses describe tusd-ip --global | grep address: | cut -b10-)
gcloud dns record-sets transaction start --zone=$ZONE_NAME
gcloud dns record-sets transaction add --zone=$ZONE_NAME --name upload.$DOMAIN_NAME. --ttl 300 --type A $STATIC_IP
gcloud dns record-sets transaction execute --zone=$ZONE_NAME

kubectl apply -f http-404-deployment.yaml
kubectl apply -f http-404-service.yaml
kubectl apply -f tusd-deployment.yaml
kubectl apply -f tusd-internal-service.yaml
kubectl apply -f tusd-service.yaml
kubectl apply -f tusd-$ENV-ingress.yaml
kubectl apply -f tusd-ingress-common.yaml
kubectl apply -f frontend-internal-tusd-hooks-service.yaml
