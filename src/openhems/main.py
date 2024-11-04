#!/usr/bin/env python3
"""
This is the OpenHEMS module. It aims to give
 Home Energy Management Automating System on house. 
 It is a back application of Home-Assistant.
More informations on https://openhomesystem.com/
"""

import sys
import os
import logging
from logging import handlers
from datetime import datetime
from threading import Thread
import argparse
from pathlib import Path
import yaml
openhemsPath = Path(__file__).parents[1]
sys.path.append(str(openhemsPath))
# pylint: disable=wrong-import-position
from openhems.modules.network.driver.home_assistant_api import HomeAssistantAPI
from openhems.modules.network.driver.fake_network import FakeNetwork
from openhems.modules.web import OpenhemsHTTPServer
from openhems.modules.util.configuration_manager import ConfigurationManager
from openhems.server import OpenHEMSServer

LOGFORMAT = '%(levelname)s : %(asctime)s : %(message)s'
LOGFILE = '/var/log/openhems/openhems.log'

class OpenHEMSApplication:
	"""
	This class is the main class to manage OpenHEMS as independant application.
	"""
	logger = None
	@staticmethod
	def filer(param=None):
		"""
		Function used to get filename on rotating log
		"""
		print("filer(",param,")")
		now = datetime.now()
		return 'openhems.'+now.strftime("%Y-%m-%d")+'.log'

	def setLogger(self, loglevel, logformat, logfile):
		"""
		Configure a logger for all the Application.
		"""
		if loglevel=="debug":
			level=logging.DEBUG
		elif loglevel in ('warn', 'warning'):
			level=logging.WARNING
		elif loglevel=="error":
			level=logging.ERROR
		elif loglevel in ('critical', 'no'):
			level=logging.CRITICAL
		else: # if loglevel=="info":
			level=logging.INFO
		rotatingFileHandler = handlers.TimedRotatingFileHandler(filename=logfile,
        	when='D',
        	interval=1,
        	backupCount=5)
		rotatingFileHandler.rotation_filename = OpenHEMSApplication.filer
		formatter = logging.Formatter(logformat)
		rotatingFileHandler.setFormatter(formatter)
		logging.basicConfig(level=level, format=logformat, handlers=[rotatingFileHandler])
		self.logger = logging.getLogger(__name__)
		self.logger.addHandler(rotatingFileHandler)
		# watched_file_handler = logging.handlers.WatchedFileHandler(logfile)
		# self.logger.addHandler(watched_file_handler)
		return self.logger

	def getLogger(self):
		"""
		Return logger
		"""
		return self.logger

	def __init__(self, yamlConfFilepath):
		# Temporary logger
		logger = logging.getLogger(__name__)
		configurator = ConfigurationManager(logger)
		configurator.addYamlConfig(Path(yamlConfFilepath))
		loglevel = configurator.get("server.loglevel")
		logformat = configurator.get("server.logformat")
		logfile = configurator.get("server.logfile")
		self.setLogger(loglevel, logformat, logfile)
		networkUpdater = None
		networkSource = configurator.get("server.network")
		if networkSource=="homeassistant":
			self.logger.info("Network: HomeAssistantAPI")
			networkUpdater = HomeAssistantAPI(configurator)
		elif networkSource=="fake":
			self.logger.info("Network: FakeNetwork")
			networkUpdater = FakeNetwork(configurator)
		else:
			self.logger.critical("OpenHEMSServer() : Unknown network source type '%s'",
				networkSource)
			sys.exit(1)
		network = networkUpdater.getNetwork()
		self.server = OpenHEMSServer(network, configurator)
		self.webserver = OpenhemsHTTPServer(network.getSchedule())
		network.notify("Start OpenHEMS.")

	def runManagementServer(self):
		"""
		Run core server (Smart part) without the webserver part. 
		"""
		self.server.run()

	def runWebServer(self):
		"""
		Run just the webserver part.
		"""
		self.webserver.run()

	def run(self):
		"""
		Run wall OpenHEMS Application
		"""
		t0 = Thread(target=self.runWebServer, args=[])
		t0.start()
		t1 = Thread(target=self.runManagementServer, args=[])
		t1.start()
		# t.join()
		# t.run()

def main():
	"""
	Simple function to run wall OpenHEMS Application
	"""
	defaultConfFilepath = os.path.dirname(__file__)+"/../../config/openhems.yaml"
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--conf', type=str, default=defaultConfFilepath,
		                help='File path to YAML configuration file.')
	args = parser.parse_args()
	app = OpenHEMSApplication(args.conf)
	app.run()

if __name__ == "__main__":
	main()
