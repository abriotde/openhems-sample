#!/bin/bash

# https://linuxfr.org/news/s-m-a-r-t-badblocks-badblocks2

source config.sh
source functions.sh

./init_server.sh

./homeassistant.sh

./openhems.sh

