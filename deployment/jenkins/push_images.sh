#!/bin/bash

docker login -u "$DOCKER_USER" -p "$DOCKER_PASSWORD" $DOCKER_REGISTRY

export DOCKER_USER=smartcommunitylab
export DOCKER_PASSWORD=C5y2ADBP
export DOCKER_EMAIL=info@smartcommunitylab.it
export DOCKER_REGISTRY=smartcommunitylab
export BUILD_NUMBER=latest

docker push $DOCKER_REGISTRY/cloud-asr-base:$BUILD_NUMBER
docker push $DOCKER_REGISTRY/cloud-asr-api:$BUILD_NUMBER
docker push $DOCKER_REGISTRY/cloud-asr-master:$BUILD_NUMBER
docker push $DOCKER_REGISTRY/cloud-asr-worker-it-small:$BUILD_NUMBER
docker push $DOCKER_REGISTRY/cloud-asr-worker-nnet3-es:$BUILD_NUMBER
docker push $DOCKER_REGISTRY/cloud-asr-web:$BUILD_NUMBER
docker push $DOCKER_REGISTRY/cloud-asr-recordings:$BUILD_NUMBER
docker push $DOCKER_REGISTRY/cloud-asr-worker:$BUILD_NUMBER
docker push $DOCKER_REGISTRY/cloud-asr-monitor:$BUILD_NUMBER

