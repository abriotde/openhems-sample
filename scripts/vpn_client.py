#!/bin/env python3
"""
Used for test VPN start/stop
"""
import os
import sys
from pathlib import Path
import logging
sys.path.append(str(Path(__file__).parents[1] / "src"))
from openhems.modules.web.driver_vpn import VpnDriverIncronClient
logger = logging.getLogger(__name__)

args = []
if len(sys.argv)>1 and sys.argv[1]=='-s':
	pathVpn = '/data/vpn'
	args = sys.argv[2:]
else:
	pathVpn = '/opt/vpn'
	args = sys.argv[1:]

command = ''
if len(args)>0:
	command = args[0]

client = VpnDriverIncronClient(logger, pathVpn)

if command=='start':
	client.startVPN()
elif command=='stop':
	client.startVPN(False)
elif command=='test':
	up = client.testVPN()
	print("Is VPN up? '",up,"'")
else:
	print(f"Unknown command : '{command}'")
