#!/bin/bash

source config.sh

$RSYNC_CMD  ../config/*.yaml homeassistant:"$HOMEASSISTANT_CONFIG_PATH/*.yaml"
$RSYNC_CMD home-assistant.sh homeassistant:~/
