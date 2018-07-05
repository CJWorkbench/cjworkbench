#!/bin/sh

set -e
set -x

CLUSTER_NAME="workbench"

## Create a cluster
#gcloud container clusters create $CLUSTER_NAME

## Save money: always shrink to the smallest number of nodes we need
#gcloud container clusters update $CLUSTER_NAME \
#  --node-pool default-pool \
#  --enable-autoscaling \
#  --min-nodes 1 \
#  --max-nodes 5

## Simplify maintenance: GCP will upgrade Kubernetes while we sleep
#gcloud container node-pools update default-pool \
#  --cluster $CLUSTER_NAME \
#  --enable-autoupgrade \
#  --enable-autorepair

#kubectl create namespace production
#kubectl create namespace staging


# 1. Create NFS volumes (ReadWriteMany volumes). TODO stop using the
# filesystem, so we can stop using NFS and end the madness.

# 1.1 Create NFS server, with a _real_ disk backing it
kubectl -n production apply -f nfs-server-pvc.yaml
kubectl -n production apply -f nfs-server-service.yaml
kubectl -n production apply -f nfs-server-deployment.yaml

# 1.2 Mount that volume (over NFS), simply to
# mkdir /importedmodules /saveddata
kubectl -n production apply -f all-nfs-data-pvc.yaml
kubectl -n production apply -f all-nfs-data-pv.yaml
kubectl -n production apply -f init-nfs-data-job.yaml
kubectl -n production wait --for=condition=complete job/init-nfs-data-job
kubectl -n production delete -f all-nfs-data-pv.yaml
kubectl -n production delete -f all-nfs-data-pvc.yaml

# 1.3 Create the volumes. After this, mounting either PersistentVolumeClaim
# will mean, "mount using NFS."
kubectl -n production apply -f saveddata-pvc.yaml
kubectl -n production apply -f saveddata-pv.yaml
kubectl -n production apply -f importedmodules-pvc.yaml
kubectl -n production apply -f importedmodules-pv.yaml

# 2. Start database
kubectl -n production apply -f dbdata-pvc.yaml
kubectl -n production apply -f database-service.yaml
kubectl -n production apply -f database-deployment.yaml

# 3. Create secrets! You'll need to be very careful here....
: ${CJW_SECRET_KEY:?"Must set CJW_SECRET_KEY"}
kubectl -n production create secret generic cjw-secret-key \
  --from-literal=value=$CJW_SECRET_KEY

: ${CJW_INTERCOM_APP_ID:?"Must set CJW_INTERCOM_APP_ID"}
: ${CJW_INTERCOM_ACCESS_TOKEN:?"Must set CJW_INTERCOM_ACCESS_TOKEN"}
kubectl -n production create secret generic cjw-intercom-secret \
  --from-literal=APP_ID=$CJW_INTERCOM_APP_ID \
  --from-literal=ACCESS_TOKEN=$CJW_INTERCOM_ACCESS_TOKEN

: ${CJW_SENDGRID_API_KEY:?"Muset set CJW_SENDGRID_API_KEY"}
kubectl -n production create secret generic cjw-sendgrid-api-key \
  --from-literal=value=$CJW_SENDGRID_API_KEY

# Never commit these files!
[ -f google-oauth-secret.json ] # we're set -e, so this will exit if missing
kubectl -n production create secret generic google-oauth-secret --from-file=json=google-oauth-secret.json

[ -f twitter-oauth-secret.json ] # we're set -e, so this will exit if missing
kubectl -n production create secret generic twitter-oauth-secret --from-file=json=twitter-oauth-secret.json

[ -f socialaccounts-secrets.json ] # we're set -e, so this will exit if missing
kubectl -n production create secret generic socialaccounts-secrets --from-file=json=socialaccounts-secrets.json

# 4. Migrate database
kubectl -n production apply -f migrate.yaml

# 5. Spin up server
kubectl -n production apply -f backend-deployment.yaml
kubectl -n production apply -f frontend-service.yaml
kubectl -n production apply -f frontend-deployment.yaml

# 6. Set up ingress to terminate SSL and direct traffic to frontend
???
