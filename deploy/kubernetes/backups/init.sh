#!/bin/sh

set -e
set -x

kubectl apply -f rbac.yaml
kubectl apply -f k8s-snapshots.yaml

PATCH='{"metadata":{"annotations":{"backup.kubernetes.io/deltas":"PT12H P14D P366D"}}}'

for ENV in staging production; do
  kubectl -n $ENV patch pvc dbdata-pvc -p "$PATCH" || true
done
