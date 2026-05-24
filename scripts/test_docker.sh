#!/bin/env bash

cd $(dirname $0)/..

# {target_arch: amd64, os_version: debian},
# {target_arch: armv7, os_version: debian},
# {target_arch: armhf, os_version: raspbian},
# {target_arch: aarch64, os_version: debian}

TARGETARCH=amd64

# docker build --build-arg TARGETARCH=$TARGETARCH -t openhems_valid .

docker build --platform linux/$TARGETARCH --build-arg TARGETARCH=$TARGETARCH -t openhems-addon:$TARGETARCH .
