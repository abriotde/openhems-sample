#!/bin/env python3
"""
Used for test VPN start/stop
"""
import sys
from pathlib import Path
import logging
# pylint: disable=wrong-import-position
# pylint: disable=import-error
sys.path.append(str(Path(__file__).parents[1] / "src"))
from openhems.modules.web.driver_vpn import VpnDriverIncronClient
logger = logging.getLogger(__name__)

args = []
if len(sys.argv)>1 and sys.argv[1]=='-s':
	VPN_PATH = '/data/vpn'
	args = sys.argv[2:]
else:
	VPN_PATH = '/opt/vpn'
	args = sys.argv[1:]
COMMAND = args[0] if len(args)>0 else ''

client = VpnDriverIncronClient(logger, VPN_PATH)

if COMMAND=='start':
	client.startVPN()
elif COMMAND=='stop':
	client.startVPN(False)
elif COMMAND=='test':
	up = client.testVPN()
	print("Is VPN up? '",up,"'")
else:
	print(f"Unknown command : '{COMMAND}'")
