#!/bin/sh

set -e
set -x

kubectl apply -f rbac.yaml
kubectl apply -f k8s-snapshots.yaml

PATCH='{"metadata":{"annotations":{"backup.kubernetes.io/deltas":"PT12H P14D P366D"}}}'

for ENV in staging production; do
  for PVC in nfs-server-pvc dbdata-pvc; do
    kubectl -n $ENV patch pvc $PVC -p "$PATCH" || true
  done
done
