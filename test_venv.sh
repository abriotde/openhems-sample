#!/bin/bash

if [ $# -ne 1 ]; then
  echo "Missing argument, expecting 'action' : 'local' or 'remote'"
  exit 1
fi

action=$1

if [ "$action" = "remote" ]; then
    echo "Run OpenHEMS server with the latest version from PyPI"
    uv venv --clear test_env
    source test_env/bin/activate
    uv pip install openhems
    uv pip show openhems
else if [ "$action" = "local" ]; then
    echo "Run OpenHEMS server with the local version"
    rm -rf dist
    uv build
    uv venv --clear test_env
    source test_env/bin/activate
    uv pip install dist/openhems-*.whl
else
  echo "Wrong argument ($action) expecting 'local' or 'remote'"
  exit 1
fi; fi

./test_venv.py
