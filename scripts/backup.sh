#!/bin/bash

source config.sh

$RSYNC_CMD homeassistant:"$HOMEASSISTANT_CONFIG_PATH/*.yaml" ../config/
# $RSYNC_CMD homeassistant:~/home-assistant.sh .
