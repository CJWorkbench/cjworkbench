#!/bin/bash

#echo 'This is more of a _log_ than an actual script you should run.'
#echo 'Exiting, to avoid breaking things in production.'
#exit 1

set -e
set -x
set -u  # unbound variables => error

type aws
type eksctl
type jq

ENV="production"  # "staging" or "production"
CLUSTER_NAME="workbench"
$DOMAIN_NAME  # or exit
$PROJECT_NAME  # or exit
$ZONE_NAME  # or exit
$APP_FQDN  # or exit
APP_STATIC_IP_NAME="app-ip"
DIR="$(dirname "$0")"

ACCOUNT_ID="$(aws sts get-caller-identity | jq -r .Account)"

eksctl create cluster \
  --name $CLUSTER_NAME \
  --version 1.20 \
  --with-oidc \
  --without-nodegroup \
  --disable-pod-imds

for service in frontend fetcher renderer cron migrate tusd; do
  aws iam create-policy \
    --policy-name $CLUSTER_NAME-$service-policy \
    --policy-document file://$DIR/iam/$service-policy.json

  eksctl create iamserviceaccount \
    --name $service-sa \
    --namespace default \
    --cluster $CLUSTER_NAME \
    --attach-policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/$CLUSTER_NAME-$service-policy" \
    --approve \
    --override-existing-serviceaccounts
done

# TODO XXX SECURITY: disable SMT in frontend+fetcher+renderer node pools, like we do on GCP
# Research https://github.com/weaveworks/eksctl/pull/578/files
eksctl create nodegroup \
  --cluster $CLUSTER_NAME \
  --name ng-demand-v1 \
  --nodes-max 4 \
  --disable-pod-imds \
  --managed \
  --instance-types t3.large

eksctl create nodegroup \
  --cluster $CLUSTER_NAME \
  --name ng-spot-v2 \
  --nodes-max 4 \
  --disable-pod-imds \
  --managed \
  --instance-types m5d.large,m5a.large,m5.large,m4.large \
  --spot

# 1 Prepare Google Cloud Storage
# 1.1 GCS account, so s3/tusd can create buckets/objects
source ./01-storage.sh

# 2. Prepare Cloud SQL
source ./02-sql.sh

TODO gotta work on the rest!

# 3. Start rabbitmq
source ./03-rabbitmq.sh

# 4. Create secrets! You'll need to be very careful here....
: ${CJW_SECRET_KEY:?"Must set CJW_SECRET_KEY"}
kubectl create secret generic cjw-secret-key \
  --from-literal=value=$CJW_SECRET_KEY

: ${CJW_INTERCOM_APP_ID:?"Must set CJW_INTERCOM_APP_ID"}
: ${CJW_INTERCOM_IDENTITY_VERIFICATION_SECRET:?"Must set CJW_INTERCOM_IDENTITY_VERIFICATION_SECRET"}
kubectl create secret generic frontend-intercom-secret \
  --from-literal=APP_ID=$CJW_INTERCOM_APP_ID \
  --from-literal=IDENTITY_VERIFICATION_SECRET=$CJW_INTERCOM_IDENTITY_VERIFICATION_SECRET

: ${CJW_INTERCOM_ACCESS_TOKEN:?"Must set CJW_INTERCOM_ACCESS_TOKEN"}
kubectl create secret generic cjw-intercom-sink-intercom-secret \
  --from-literal=ACCESS_TOKEN=$CJW_INTERCOM_ACCESS_TOKEN

: ${CJW_SENDGRID_API_KEY:?"Muset set CJW_SENDGRID_API_KEY"}
kubectl create secret generic cjw-sendgrid-api-key \
  --from-literal=value=$CJW_SENDGRID_API_KEY

: ${STRIPE_PUBLIC_API_KEY:?"Muset set STRIPE_PUBLIC_API_KEY"}
: ${STRIPE_API_KEY:?"Muset set STRIPE_API_KEY"}
: ${STRIPE_WEBHOOK_SIGNING_SECRET:?"Muset set STRIPE_WEBHOOK_SIGNING_SECRET"}
kubectl create secret generic cjw-stripe-secret \
  --from-literal=STRIPE_PUBLIC_API_KEY="$STRIPE_PUBLIC_API_KEY" \
  --from-literal=STRIPE_API_KEY="$STRIPE_API_KEY" \
  --from-literal=STRIPE_WEBHOOK_SIGNING_SECRET="$STRIPE_WEBHOOK_SIGNING_SECRET" \

# Never commit these files!
[ -f google-oauth-secret.json ] # we're set -e, so this will exit if missing
kubectl create secret generic google-oauth-secret --from-file=json=google-oauth-secret.json

[ -f intercom-oauth-secret.json ] # we're set -e, so this will exit if missing
kubectl create secret generic intercom-oauth-secret --from-file=json=intercom-oauth-secret.json

[ -f twitter-oauth-secret.json ] # we're set -e, so this will exit if missing
kubectl create secret generic twitter-oauth-secret --from-file=json=twitter-oauth-secret.json

# 5. Migrate database
kubectl create configmap workbench-config \
  --from-literal=environment=$ENV \
  --from-literal=domainName=$DOMAIN_NAME \
  --from-literal=appDomainName=$APP_FQDN \
  --from-literal=canonicalUrl="https://$APP_FQDN"
kubectl create configmap gcloud-config \
  --from-literal=PROJECT_NAME=$PROJECT_NAME
kubectl run migrate-cluster-setup \
  --image="gcr.io/workbenchdata-ci/migrate:latest" \
  -i --rm --quiet \
  --restart=Never \
  --overrides="$(cat migrate.json | sed -e 's/$SHA/latest/')"

# 6. Spin up server
kubectl apply -f fetcher-deployment.yaml
kubectl apply -f renderer-deployment.yaml
kubectl apply -f cron-deployment.yaml
kubectl apply -f frontend-ingress-common.yaml
kubectl apply -f frontend-service.yaml
kubectl apply -f frontend-deployment.yaml

# 7. Set up ingress to terminate SSL and direct traffic to frontend
gcloud compute addresses create $APP_STATIC_IP_NAME --global
kubectl apply -f frontend-$ENV-ingress.yaml
STATIC_IP=$(gcloud compute addresses describe $APP_STATIC_IP_NAME --global | grep address: | cut -b10-)
gcloud dns record-sets transaction start --zone=$ZONE_NAME
gcloud dns record-sets transaction add --zone=$ZONE_NAME --name $APP_FQDN. --ttl 300 --type A $STATIC_IP
gcloud dns record-sets transaction execute --zone=$ZONE_NAME

# 8. Set up ingress to terminate SSL and direct traffic to tusd
source 08-tusd.sh

# 9. Set up CDN for static files
source 09-static-files.sh
