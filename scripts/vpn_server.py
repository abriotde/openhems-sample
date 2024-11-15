#!/bin/env python3
"""
Script to start/stop/test VPN on host.
To be placed on incrontab like this:
/data/vpn/request	IN_ATTRIB,IN_CLOSE_WRITE	$OPENHEMS_PATH/scripts/vpn_server.py
"""

import sys
import logging
from pathlib import Path
# pylint: disable=wrong-import-position
# pylint: disable=import-error
sys.path.append(str(Path(__file__).parents[1] / "src"))
from openhems.modules.web.driver_vpn import VpnDriverIncronServer
logger = logging.getLogger(__name__)


server = VpnDriverIncronServer(logger, "/data/vpn")
server.run()
