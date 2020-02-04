#!/bin/sh

set -e
set -x

DIR="$(dirname "$0")"

export APP_INSTANCE_NAME=rabbitmq-1
export NAMESPACE="default"
export REPLICAS=3
export RABBITMQ_ERLANG_COOKIE=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1 | tr -d '\n' | base64)
export RABBITMQ_DEFAULT_USER=rabbit
export RABBITMQ_DEFAULT_PASS=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1 | tr -d '\n' | base64)

TAG=3.7
export IMAGE_RABBITMQ=marketplace.gcr.io/google/rabbitmq:${TAG}
export IMAGE_RABBITMQ_INIT=marketplace.gcr.io/google/rabbitmq/debian9:${TAG}

# Pin to specific images at the time this script of run, instead of launching
# instances at $TAG (which points to different images on different days)
for i in "IMAGE_RABBITMQ" "IMAGE_RABBITMQ_INIT"; do
  repo=$(echo ${!i} | cut -d: -f1);
  digest=$(docker pull ${!i} | sed -n -e 's/Digest: //p');
  export $i="$repo@$digest";
  env | grep $i;
done

# Expand templates

# Define name of service account
export RABBITMQ_SERVICE_ACCOUNT=$APP_INSTANCE_NAME-rabbitmq-sa
# Expand rbac.yaml.template
envsubst '$APP_INSTANCE_NAME' < "$DIR"/scripts/rbac.yaml.template > "${DIR}/${APP_INSTANCE_NAME}_rbac.yaml"

awk 'FNR==1 {print "---"}{print}' "$DIR"/manifest/* \
  | envsubst '$APP_INSTANCE_NAME $NAMESPACE $IMAGE_RABBITMQ $IMAGE_RABBITMQ_INIT $REPLICAS $RABBITMQ_ERLANG_COOKIE $RABBITMQ_DEFAULT_USER $RABBITMQ_DEFAULT_PASS $RABBITMQ_SERVICE_ACCOUNT' \
  > "${DIR}/${APP_INSTANCE_NAME}_manifest.yaml"

# rbac.yaml
kubectl apply -f "${DIR}/${APP_INSTANCE_NAME}_rbac.yaml" --namespace "${NAMESPACE}"
# manifest.yaml
kubectl apply -f "${DIR}/${APP_INSTANCE_NAME}_manifest.yaml" --namespace "${NAMESPACE}"
