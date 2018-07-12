#!/bin/sh

set -e
set -x

kubectl apply -f certificate-crd.yaml
kubectl apply -f issuer-crd.yaml
kubectl apply -f clusterissuer-crd.yaml
kubectl apply -f serviceaccount.yaml
kubectl apply -f rbac.yaml
kubectl apply -f deployment.yaml

# service-account.json is super-secret. It must grant access to Cloud DNS
# admin.
[ -f service-account.json ] # or fail
kubectl -n kube-system create secret generic clouddns-svc-secret \
  --from-file=service-account.json

kubectl apply -f letsencrypt.yaml
