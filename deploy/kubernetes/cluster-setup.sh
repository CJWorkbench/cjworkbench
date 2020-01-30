#!/bin/bash

#echo 'This is more of a _log_ than an actual script you should run.'
#echo 'Exiting, to avoid breaking things in production.'
#exit 1

set -e
set -x

ENV="staging"  # or "production", or....
PROJECT_NAME="workbench-$ENV"  # Google Cloud Project
CLUSTER_NAME="workbench"
if [ "$ENV" = "staging" ]; then
  DOMAIN_NAME="workbenchdata-staging.com"
else
  DOMAIN_NAME="workbenchdata.com"
fi
ZONE_NAME="workbench-zone"
APP_FQDN="app.$DOMAIN_NAME"
APP_STATIC_IP_NAME="app-ip"

# Choose the GCloud project. We build one cluster per project.
gcloud config configurations create $PROJECT_NAME
gcloud config configurations activate $PROJECT_NAME
gcloud auth login
gcloud config set project $PROJECT_NAME
gcloud config set container/cluster workbench

# Harden service account security
# https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster#use_least_privilege_sa
#
# Quoth https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity:
#
#     All Kubernetes service accounts that share a name, Namespace name, and
#     Identity Namespace share access to GSAs.
#
# ... so give each service account a different GSA
gcloud iam service-accounts create $CLUSTER_NAME-least-privilege-sa \
  --display-name=$CLUSTER_NAME-least-privilege-sa

gcloud projects add-iam-policy-binding $PROJECT_NAME \
  --member "serviceAccount:$CLUSTER_NAME-least-privilege-sa@$PROJECT_NAME.iam.gserviceaccount.com" \
  --role roles/logging.logWriter

gcloud projects add-iam-policy-binding $PROJECT_NAME \
  --member "serviceAccount:$CLUSTER_NAME-least-privilege-sa@$PROJECT_NAME.iam.gserviceaccount.com" \
  --role roles/monitoring.metricWriter

gcloud projects add-iam-policy-binding $PROJECT_NAME \
  --member "serviceAccount:$CLUSTER_NAME-least-privilege-sa@$PROJECT_NAME.iam.gserviceaccount.com" \
  --role roles/monitoring.viewer

echo "Browse to https://console.cloud.google.com/apis/library/container.googleapis.com?project=workbench-staging"
echo "to enable the Kubernetes Engine API"
echo
echo "When done, press Enter:"
read

# Create a cluster
#
# * identity-namespace: we use Workflow Identity, so http://metadata/ doesn't leak passwords
# * disable basic auth (security)
# * Enable Stackdriver logging
# * VPC-native (saves a network hop when load-balancing HTTP)
gcloud beta container clusters create $CLUSTER_NAME \
  --identity-namespace=$PROJECT_NAME.svc.id.goog \
  --no-enable-basic-auth \
  --enable-stackdriver-kubernetes \
  --zone=us-central1-b \
  --enable-ip-alias \
  --metadata disable-legacy-endpoints=true


# Grant yourself the ability to create roles in Kubernetes
kubectl create clusterrolebinding cluster-admin-binding \
  --clusterrole cluster-admin \
  --user $(gcloud config get-value account)


# Make the "gke-smt-disabled" flag do something useful.
#
# This only affects newly-created nodes. So we'll create a new node pool after.
kubectl create -f \
  https://raw.githubusercontent.com/GoogleCloudPlatform/k8s-node-tools/master/disable-smt/gke/disable-smt.yaml


## Build a node pool with all the settings we want
#
# * size 1-9 machines
# * disable hyperthreading, because we run untrusted code
#   see https://cloud.google.com/kubernetes-engine/docs/security-bulletins#may-14-2019
# * 6-vCPU machines because after we disable hyperthreading, it's really 3.
#   4-vCPU would prevent us from scheduling two renderers on the same node
#   because we lose a bit of CPU to overhead. For instance, 4-vCPU would give
#   ~1.75 CPUs for our own tasks (and a fetcher/renderer costs 1 CPU).
# * 12GB RAM: [2019-11-06] we give renderer 5GB RAM; leave room for 2.
# * no gvisor for now, since it'll take new deployment YAML
# * $CLUSTER_NAME-least-privilege-sa: see
#   https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster#use_least_privilege_sa
gcloud beta container node-pools create main-pool \
  --cluster=$CLUSTER_NAME \
  --service-account=$CLUSTER_NAME-least-privilege-sa@$PROJECT_NAME.iam.gserviceaccount.com \
  --machine-type=custom-6-12288 \
  --enable-autoupgrade \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 9 \
  --node-labels=cloud.google.com/gke-smt-disabled=true \
  --metadata disable-legacy-endpoints=true \
  --workload-metadata-from-node=GKE_METADATA_SERVER \
  --zone=us-central1-b

gcloud beta container node-pools delete default-pool --zone=us-central1-b

# [STAGING ONLY] Grant Cloud Build the permissions to call kubectl:
# In GCP Console, visit the IAM menu.
# From the list of service accounts, click the Roles drop-down menu beside the Cloud Build [YOUR-PROJECT-ID]@cloudbuild.gserviceaccount.com service account.
# Click Kubernetes Engine, then click Kubernetes Engine Admin.
# Click Save.

# Enable "Application" resources (we use one for RabbitMQ)
kubectl apply -f "https://raw.githubusercontent.com/GoogleCloudPlatform/marketplace-k8s-app-tools/master/crd/app-crd.yaml"

# Enable SSD storage class
kubectl apply -f ssd-storageclass.yaml

# 1 Prepare Google Cloud Storage and Minio
# 1.1 GCS account, so minio can create buckets/objects
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
gsutil mb gs://user-files.$DOMAIN_NAME
gsutil mb gs://static.$DOMAIN_NAME
gsutil mb gs://stored-objects.$DOMAIN_NAME
gsutil mb gs://external-modules.$DOMAIN_NAME
gsutil mb gs://cached-render-results.$DOMAIN_NAME
gsutil ubla set on gs://user-files.$DOMAIN_NAME
gsutil ubla set on gs://static.$DOMAIN_NAME
gsutil ubla set on gs://stored-objects.$DOMAIN_NAME
gsutil ubla set on gs://external-modules.$DOMAIN_NAME
gsutil ubla set on gs://cached-render-results.$DOMAIN_NAME
gsutil iam ch allUsers:objectViewer gs://static.$DOMAIN_NAME
echo '[{"origin":"*","method":"GET","maxAgeSeconds":3000}]' > static-cors.json \
  && gsutil cors set static-cors.json gs://static.$DOMAIN_NAME \
  && rm -f static-cors.json
gcloud dns record-sets transaction start --zone=$ZONE_NAME
gcloud dns record-sets transaction add --zone $ZONE_NAME --name static.$DOMAIN_NAME. --ttl 7200 --type CNAME c.storage.googleapis.com.
gcloud dns record-sets transaction execute --zone $ZONE_NAME

gcloud iam service-accounts keys create application_default_credentials.json \
  --iam-account $CLUSTER_NAME-minio@$PROJECT_NAME.iam.gserviceaccount.com
kubectl create secret generic minio-gcs-credentials \
  --from-file=./application_default_credentials.json
rm application_default_credentials.json

# 2. Start database+rabbitmq+minio
kubectl apply -f dbdata-pvc.yaml
kubectl apply -f database-service.yaml
kubectl apply -f database-deployment.yaml
rabbitmq/init.sh
minio/init.sh $ENV

# 3. Create secrets! You'll need to be very careful here....
: ${CJW_SECRET_KEY:?"Must set CJW_SECRET_KEY"}
kubectl create secret generic cjw-secret-key \
  --from-literal=value=$CJW_SECRET_KEY

: ${CJW_INTERCOM_APP_ID:?"Must set CJW_INTERCOM_APP_ID"}
: ${CJW_INTERCOM_ACCESS_TOKEN:?"Must set CJW_INTERCOM_ACCESS_TOKEN"}
kubectl create secret generic cjw-intercom-secret \
  --from-literal=APP_ID=$CJW_INTERCOM_APP_ID \
  --from-literal=ACCESS_TOKEN=$CJW_INTERCOM_ACCESS_TOKEN

: ${CJW_SENDGRID_API_KEY:?"Muset set CJW_SENDGRID_API_KEY"}
kubectl create secret generic cjw-sendgrid-api-key \
  --from-literal=value=$CJW_SENDGRID_API_KEY

# Never commit these files!
[ -f google-oauth-secret.json ] # we're set -e, so this will exit if missing
kubectl create secret generic google-oauth-secret --from-file=json=google-oauth-secret.json

[ -f intercom-oauth-secret.json ] # we're set -e, so this will exit if missing
kubectl create secret generic intercom-oauth-secret --from-file=json=intercom-oauth-secret.json

[ -f twitter-oauth-secret.json ] # we're set -e, so this will exit if missing
kubectl create secret generic twitter-oauth-secret --from-file=json=twitter-oauth-secret.json

# 4. Migrate database
kubectl create configmap workbench-config \
  --from-literal=environment=$ENV \
  --from-literal=domainName=$DOMAIN_NAME \
  --from-literal=domainNameWithLeadingDot=.$DOMAIN_NAME \
  --from-literal=appDomainName=$APP_FQDN \
  --from-literal=canonicalUrl="https://$APP_FQDN"
kubectl run migrate-cluster-setup \
  --image="gcr.io/cj-workbench/migrate:latest" \
  -i --rm --quiet \
  --restart=Never \
  --overrides="$(cat migrate.json | sed -e 's/$SHA/latest/')"

# 5. Spin up server
kubectl apply -f fetcher-deployment.yaml
kubectl apply -f renderer-deployment.yaml
kubectl apply -f cron-deployment.yaml
kubectl apply -f frontend-ingress-common.yaml
kubectl apply -f frontend-service.yaml
kubectl apply -f frontend-deployment.yaml

# 6. Set up ingress to terminate SSL and direct traffic to frontend
gcloud compute addresses create $APP_STATIC_IP_NAME --global
kubectl apply -f frontend-$ENV-ingress.yaml
STATIC_IP=$(gcloud compute addresses describe $APP_STATIC_IP_NAME --global | grep address: | cut -b10-)
gcloud dns record-sets transaction start --zone=$ZONE_NAME
gcloud dns record-sets transaction add --zone=$ZONE_NAME --name $APP_FQDN. --ttl 300 --type A $STATIC_IP
gcloud dns record-sets transaction execute --zone=$ZONE_NAME

# 7. Backups
backups/init.sh
