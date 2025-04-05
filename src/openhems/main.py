#!/usr/bin/env python3
"""
This is the OpenHEMS module. It aims to give
 Home Energy Management Automating System on house. 
 It is a back application of Home-Assistant.
More informations on https://openhomesystem.com/
"""

import sys
import logging
from logging import handlers
from datetime import datetime
from threading import Thread
import argparse
from pathlib import Path
from requests.exceptions import ConnectTimeout
openhemsPath = Path(__file__).parents[1]
sys.path.append(str(openhemsPath))
# pylint: disable=wrong-import-position
from openhems.modules.network import network_helper
from openhems.modules.web import OpenhemsHTTPServer
from openhems.modules.util import (
	ConfigurationManager, ConfigurationException,
	CastUtililty
)
from openhems.server import OpenHEMSServer
class OpenHEMSApplication:
	"""
	This class is the main class to manage OpenHEMS as independant application.
	"""
	@staticmethod
	def filer(param=None):
		"""
		Function used to get filename on rotating log
		"""
		print("filer(",param,")")
		now = datetime.now()
		return 'openhems.'+now.strftime("%Y-%m-%d")+'.log'

	def setLogger(self, loglevel, logformat, logfile, inDocker=False):
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
		myHandlers = []
		fileHandler = None
		formatter = logging.Formatter(logformat)
		# Case wrong logfile path : set to empty : no logging file
		logfileparents = Path(logfile).parents
		if len(logfileparents)==0 or not logfileparents[0].is_dir():
			logfile = "" # No log file
		if not inDocker and logfile!="":
			fileHandler = handlers.TimedRotatingFileHandler(filename=logfile,
	        	when='D',
	        	interval=1,
	        	backupCount=5)
			fileHandler.rotation_filename = OpenHEMSApplication.filer
			fileHandler.setFormatter(formatter)
			myHandlers.append(fileHandler)
		fileHandler = logging.StreamHandler(sys.stdout)
		fileHandler.setFormatter(formatter)
		myHandlers.append(fileHandler)
		logging.basicConfig(level=level, format=logformat, handlers=myHandlers)
		self.logger = logging.getLogger(__name__)
		# self.logger.addHandler(fileHandler)
		# watched_file_handler = logging.handlers.WatchedFileHandler(logfile)
		# self.logger.addHandler(watched_file_handler)
		return self.logger

	def getLogger(self):
		"""
		Return logger
		"""
		return self.logger

	def loadYamlConfiguration(self, configurator:ConfigurationManager, yamlConfFilepath:str):
		"""
		Load YAML configuration, over load it with a secret file if exists.
		Return a "Configurator"
		"""
		# print("Load YAML configuration from '",yamlConfFilepath,"'")
		path = Path(yamlConfFilepath)
		configurator.addYamlConfig(path)
		if path.suffix!="":
			# print("Suffix:", path.suffix)
			secretPath = str(yamlConfFilepath).replace(path.suffix, ".secret"+path.suffix)
			path = Path(secretPath)
			if path.is_file():
				# print("Over load YAML configuration with '",str(path),"'")
				configurator.addYamlConfig(path)
			# else: print("No '",str(path),"'")
		configurator.completeWithDefaults()
		return configurator

	def __init__(self, yamlConfFilepath:str, *, port=0, logfilepath='', inDocker=False):
		# Temporary logger
		self.logger = logging.getLogger(__name__)
		# Keep warnings for tests (self.server can be None if it raise Exception).
		self.warnings = []
		network = None
		schedule = []
		configurator = ConfigurationManager(self.logger)
		try:
			configurator = self.loadYamlConfiguration(configurator, yamlConfFilepath)
		except ConfigurationException as e:
			self.warnings.append(str(e))
		loglevel = configurator.get("server.loglevel")
		logformat = configurator.get("server.logformat")
		logfile = logfilepath if logfilepath!='' else configurator.get("server.logfile")
		self.setLogger(loglevel, logformat, logfile, inDocker)
		self.logger.info("Load YAML configuration from '%s'.",yamlConfFilepath)
		self.server = None
		try:
			network = network_helper.getNetworkFromConfiguration(self.logger, configurator)
			self.warnings = self.warnings + network.getWarningMessages()
			self.server = OpenHEMSServer(self.logger, network, configurator)
			schedule = self.server.getSchedule()
		except (ConfigurationException, ConnectTimeout) as e:
			self.logger.error(str(e))
			self.warnings.append(str(e))
		for warning in self.warnings:
			self.logger.error(warning)
		port = port if port>0 else configurator.get("server.port")
		port = CastUtililty.toTypeInt(port)
		root = configurator.get("server.htmlRoot")
		inDocker = inDocker or configurator.get("server.inDocker", "bool")
		self.webserver = OpenhemsHTTPServer(self.logger, schedule, self.warnings,
			port=port, htmlRoot=root, inDocker=inDocker, configurator=configurator)
		if network is not None:
			self.logger.info("OpenHEMS loaded.")
			network.notify("Start OpenHEMS.")

	def runManagementServer(self):
		"""
		Run core server (Smart part) without the webserver part. 
		"""
		if self.server is not None:
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
	defaultConfFilepath = Path(__file__).parents[2] / "config/openhems.yaml"
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--conf', type=str, default=str(defaultConfFilepath),
		help='File path to YAML configuration file.')
	parser.add_argument('-p', '--port', type=int, default=0,
		help='HTTP web server port.')
	parser.add_argument('-d', '--docker', default=False, action='store_true',
		help="""If this option is set, run as it run on docker container.
			If not set, consider it is not in docker
			except if configuration key server.inDocker = True """)
	parser.add_argument('-l', '--logfile', type=str, default='',
		help='Log file path.')
	args = parser.parse_args()
	app = OpenHEMSApplication(args.conf, port=args.port,
		logfilepath=args.logfile, inDocker=args.docker)
	app.run()

if __name__ == "__main__":
	main()
