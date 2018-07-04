#!/bin/sh

CLUSTER_NAME="workbench"

## Create a cluster
#gcloud container clusters create $CLUSTER_NAME

## Save money: always shrink to the smallest number of nodes we need
#gcloud container clusters update $CLUSTER_NAME \
#  --node-pool default-pool \
#  --enable-autoscaling \
#  --min-nodes 1 \
#  --max-nodes 5 \

## Simplify maintenance: GCP will upgrade Kubernetes while we sleep
#gcloud container node-pools update default-pool \
#  --cluster $CLUSTER_NAME \
#  --enable-autoupgrade \
#  --enable-autorepair

#kubectl create namespace production
#kubectl create namespace staging

kubectl -n production apply -f nfs-server-pvc.yaml
kubectl -n production apply -f nfs-server-service.yaml
kubectl -n production apply -f nfs-server-deployment.yaml

kubectl -n production apply -f dbdata-pvc.yaml
kubectl -n production apply -f saveddata-pvc.yaml
kubectl -n production apply -f saveddata-pv.yaml
kubectl -n production apply -f importedmodules-pvc.yaml
kubectl -n production apply -f importedmodules-pv.yaml

kubectl -n production apply -f database-service.yaml
kubectl -n production apply -f database-deployment.yaml

kubectl -n production apply -f migrate.yaml
