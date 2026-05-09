#!/bin/env python

import sys
import os
import logging
from time import sleep

sys.path.append(os.path.dirname(__file__))
from streamlit_app import OpenhemsHTTPServer2, OpenHEMSContext

from openhems.modules.web import OpenHEMSSchedule
import threading
from threading import Thread
from openhems.modules.util import ProjectConfiguration
from openhems.modules.web.unix_socket import UnixSocketServer

logger = logging.getLogger(__name__)
import socket
import json
import threading
import os


def listen_socket():
	# Simulate listening to a socket and updating the schedule
	while True:
		print("Listening to socket...")
		sleep(5)

def root_run(context):
	socket = UnixSocketServer(context.schedule, context.lock, context.logger)
	socket.start()
	try:
		while True:
			print("Schedules:")
			for node_id, node in context.schedule.items():
				print(" - ", node_id, "-", node)
			sleep(10)
	except KeyboardInterrupt:
		socket.stop()

def streamlit_test():
	"""
	Test function to run Streamlit app without running the whole OpenHEMS application.
	"""
	# Create a dummy context with necessary attributes
	dummy_context = OpenHEMSContext(
		lock=threading.Lock(),
		schedule={"node_id": OpenHEMSSchedule(3600, "Test Schedule")},
		logger=logger,
		configurator=None,
		translations={"web": {"defaultTooltip": "Default: tooltip"}},
		vpnDriver=None
	)
	# Run the Streamlit app
	server = OpenhemsHTTPServer2(
		mylogger=dummy_context.logger,
		schedule=dummy_context.schedule,
		warningMessages=[],
		port=8501,  # Default Streamlit port
		inDocker=False,
		configurator=dummy_context.configurator
	)
	t0 = Thread(target=root_run, args=[dummy_context], daemon=True)
	t0.start()
	server.run()
	t0.join(timeout=5)


streamlit_test()
