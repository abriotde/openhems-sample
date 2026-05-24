#!/bin/env bash

OPENHEMS_PATH=$(pwd)
TARGETARCH=amd64

cd $(dirname $0)/..
mkdir -p logs

OPENHEMS_LOGPATH=$(pwd)/logs

# {target_arch: amd64, os_version: debian}, OK
# {target_arch: aarch64, os_version: debian}, OK = arm64
# {target_arch: armv7, os_version: debian}, = 32 bit homeassistant/armv7-homeassistant
# {target_arch: armhf, os_version: raspbian}, = armv7l = 32 bit avec FPU

action=$1

if [ $# != 1 ]; then
    echo "Missing argument action : build|run"
    exit
fi

if [ $action == "build" ]; then
    echo "Build docker 'openhems-addon'"
    # docker build --build-arg TARGETARCH=$TARGETARCH -t openhems_valid .
    docker build --platform linux/$TARGETARCH --build-arg TARGETARCH=$TARGETARCH -t openhems-addon:$TARGETARCH .
elif [ $action == "run" ]; then
    cmd="docker run -p 8000:8000 \
        -v $OPENHEMS_PATH/config:/app/config \
        -v $OPENHEMS_LOGPATH:/log \
        openhems-addon:$TARGETARCH"
    echo "$ $cmd"
    docker run -p 8000:8000 \
        -v $OPENHEMS_PATH/config:/app/config \
        -v $OPENHEMS_LOGPATH:/log \
        openhems-addon:$TARGETARCH
fi