#!/bin/env python3

import sys
import logging
sys.path.append(str(Path(__file__).parents[1] / "src"))
from openhems.modules.web.driver_vpn import VpnDriverIncronServer
logger = logging.getLogger(__name__)


server = VpnDriverIncronServer(logger, "/data/vpn")
server.run()
