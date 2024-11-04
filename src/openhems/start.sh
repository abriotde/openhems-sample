#!/bin/bash

args=$*
echo "ARGS:$args"

script_dir=`dirname $0`
cd $script_dir/../../
/bin/bash -c ". ./venvemhass/bin/activate; exec ./src/openhems/main.py $args"

