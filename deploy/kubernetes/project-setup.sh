#!/bin/bash

echo 'This is more of a _log_ than an actual script you should run.'
echo 'Exiting, to avoid breaking things in production.'
exit 1

set -e
set -x

PROJECT_NAME="cj-workbench"  # Google Cloud Project

# minio needs storage.buckets.list, or it prints lots of errors.
# (which seems like a bug.... https://github.com/minio/mc/issues/2652)
# Minio uses this permission to poll for bucket policies.
gcloud iam roles create MinioStorageBucketsList \
  --project=$PROJECT_NAME \
  --permissions=storage.buckets.list
