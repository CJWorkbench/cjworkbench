#!/bin/bash

set -ex

DIR="$(dirname "$0")"
ENV=${1:?"Usage: $0 ENVIRONMENT"}

# Now use the root user to generate the non-root user.
kubectl -n "$ENV" run minio-adduser \
  -i --rm=true \
  --restart=Never \
  --image=minio/mc:RELEASE.2019-10-09T22-54-57Z \
  --overrides='
    {
      "spec": {
        "containers": [{
          "name": "minio-adduser",
          "image": "minio/mc:RELEASE.2019-10-09T22-54-57Z",
          "command": [
            "sh", "-c",
            "while ! nc -z minio-service 80; do sleep 0.1; done; mc config host add workbench http://minio-service \"$ROOT_ACCESS_KEY\" \"$ROOT_SECRET_KEY\" && mc admin user add workbench \"$ACCESS_KEY\" \"$SECRET_KEY\" && mc admin policy set workbench readwrite user=\"$ACCESS_KEY\""
          ],
          "env": [
            {"name": "ROOT_ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "minio-root-access-key", "key": "access_key"}}},
            {"name": "ROOT_SECRET_KEY", "valueFrom": {"secretKeyRef": {"name": "minio-root-access-key", "key": "secret_key"}}},
            {"name": "ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "minio-access-key", "key": "access_key"}}},
            {"name": "SECRET_KEY", "valueFrom": {"secretKeyRef": {"name": "minio-access-key", "key": "secret_key"}}}
          ]
        }]
      }
    }'
