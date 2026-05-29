#!/bin/env python3
"""
File used to test openhems as a package (see test_venv.sh)
"""

#pylint: disable=invalid-name

import openhems

config_file = "./config/openhems.yaml"

app = openhems.OpenHEMSApplication(config_file)
app.run()
