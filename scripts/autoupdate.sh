#!/bin/bash

source config.sh

mkdir -p $TMP_DIR/openhems-sample
TMP_DIR=$TMP_DIR/openhems-sample


export OPENHEMS_PATH
export OPENHEMS_USER
export OPENHEMS_BRANCH
export TMP_DIR

./autoupdate.py

