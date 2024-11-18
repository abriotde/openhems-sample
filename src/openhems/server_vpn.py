#!/usr/bin/env python3
"""
This is the OpenHEMS module. It aims to give
 Home Energy Management Automating System on house. 
 It is a back application of Home-Assistant.
More informations on https://openhomesystem.com/
"""

import sys
import logging
from pathlib import Path
openhemsPath = Path(__file__).parents[1]
sys.path.append(str(openhemsPath))
# pylint: disable=wrong-import-position
from openhems.modules.web.driver_vpn import VpnDriverIncronServer
logger = logging.getLogger(__name__)

server = VpnDriverIncronServer(logger)
server.runServer()
