#!/bin/bash

rm -rf dist
uv build
uv venv --clear test_env
source test_env/bin/activate
uv pip install dist/openhems-*.whl
./test_venv.py
