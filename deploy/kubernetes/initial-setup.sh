#!/bin/sh

echo 'This is more of a _log_ than an actual script you should run.'
echo 'Exiting, to avoid breaking things in production.'
exit 1

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

# 1.4 Prepare Google Cloud Storage and Minio
# 1.4.1 GCS account, so minio can create buckets/objects
gcloud iam service-accounts create production-minio --display-name production-minio
gsutil mb gs://production-user-files.workbenchdata.com
gsutil mb gs://production-static.workbenchdata.com
gsutil acl set public-read gs://production-static.workbenchdata.com
gsutil acl ch -u production-minio@cj-workbench.iam.gserviceaccount.com:W gs://production-user-files.workbenchdata.com
gsutil acl ch -u production-minio@cj-workbench.iam.gserviceaccount.com:W gs://production-static.workbenchdata.com
gcloud dns record-sets transaction start --zone=workbenchdata-com
gcloud dns record-sets transaction add --zone workbenchdata-com --name production-static.workbenchdata.com. --ttl 7200 --type CNAME c.storage.googleapis.com.
gcloud dns record-sets transaction execute --zone workbenchdata-com

gcloud iam service-accounts keys create application_default_credentials.json \
  --iam-account production-minio@cj-workbench.iam.gserviceaccount.com
kubectl -n production create secret generic minio-gcs-credentials \
  --from-file=./application_default_credentials.json
rm application_default_credentials.json
# 1.4.2 minio access key and secret key
#docker run --name minio-genkey --rm minio/minio server /nodata and after it prints info, Ctrl+C
kubectl -n production create secret generic minio-access-key \
  --from-literal=access_key="$MINIO_ACCESS_KEY" \
  --from-literal=secret_key="$MINIO_SECRET_KEY" \
  --from-literal=external_url="https://production-user-files.workbenchdata.com" \
  --from-literal=bucket_prefix=""

# 2. Start database+rabbitmq+minio
kubectl -n production apply -f dbdata-pvc.yaml
kubectl -n production apply -f database-service.yaml
kubectl -n production apply -f database-deployment.yaml
kubectl -n production apply -f rabbitmq-service.yaml
kubectl -n production apply -f rabbitmq-deployment.yaml
kubectl -n production apply -f minio-service.yaml
kubectl -n production apply -f minio-deployment.yaml

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

[ -f socialaccount-secrets.json ] # we're set -e, so this will exit if missing
kubectl -n production create secret generic socialaccount-secrets --from-file=json=socialaccount-secrets.json

# 4. Migrate database
kubectl -n production apply -f migrate.yaml

# 5. Spin up server
kubectl -n production apply -f worker-deployment.yaml
kubectl -n production apply -f cron-deployment.yaml
kubectl -n production apply -f frontend-service.yaml
kubectl -n production apply -f frontend-deployment.yaml

# 6. Set up ingress to terminate SSL and direct traffic to frontend

# 6.1 Cluster-wide config: create one nginx controller and one SSL cert manager
cert-manager/init.sh
kubectl apply -f nginx-mandatory.yaml # creates+uses ingress-nginx namespace
kubectl apply -f nginx-config.yaml # StackDriver-friendly logging
kubectl apply -f static-ip-svc.yaml
echo -n 'Waiting for external IP... ' >&2
EXTERNAL_IP='<none>'
while [ "$EXTERNAL_IP" = "<none>" ]; do
  sleep 1
  EXTERNAL_IP=$(kubectl -n ingress-nginx get service nginx-ingress-lb -o custom-columns=x:status.loadBalancer.ingress[0].ip | tail -n1)
done
echo "$EXTERNAL_IP"
# Make static IP persist. https://github.com/kubernetes/ingress-nginx/tree/master/docs/examples/static-ip
kubectl -n ingress-nginx patch service nginx-ingress-lb -p '{"spec":{"loadBalancerIP":"'$EXTERNAL_IP'"}}'
gcloud compute addresses create nginx-ingress-lb --addresses "$EXTERNAL_IP" --region us-central1

kubectl apply -f frontend-production-ingress.yaml
kubectl apply -f minio-production-ingress.yaml
???

# 7. Backups
backups/init.sh
