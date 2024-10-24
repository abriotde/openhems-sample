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
from datetime import datetime
from threading import Thread
import yaml
from openhems.modules.network.driver.home_assistant_api import HomeAssistantAPI
from openhems.modules.web import OpenhemsHTTPServer
from .server import OpenHEMSServer

yaml_conf = os.path.dirname(__file__)+"/../../config/openhems.yaml"
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
		rotating_file_handler = logging.handlers.TimedRotatingFileHandler(filename=logfile,
        	when='D',
        	interval=1,
        	backupCount=5)
		rotating_file_handler.rotation_filename = OpenHEMSApplication.filer
		formatter = logging.Formatter(logformat)
		rotating_file_handler.setFormatter(formatter)
		logging.basicConfig(level=level, format=logformat, handlers=[rotating_file_handler])
		self.logger = logging.getLogger(__name__)
		self.logger.addHandler(rotating_file_handler)
		# watched_file_handler = logging.handlers.WatchedFileHandler(logfile)
		# self.logger.addHandler(watched_file_handler)
		return self.logger

	def getLogger(self):
		"""
		Return logger
		"""
		return self.logger

	def __init__(self, yaml_conf_filepath):
		conf = None
		network = None
		serverConf = None
		with open(yaml_conf_filepath, 'r', encoding="utf-8") as file:
			print(f"Load YAML configuration from '{yaml_conf_filepath}'")
			conf = yaml.load(file, Loader=yaml.FullLoader)
			try:
				serverConf = conf['server']
				loglevel = serverConf.get("loglevel", "info")
				logformat = serverConf.get("logformat", LOGFORMAT)
				logfile = serverConf.get("logfile", LOGFILE)
				self.setLogger(loglevel, logformat, logfile)
				self.logger.info("Load YAML configuration from '%s'",
					yaml_conf_filepath)
				networkUpdater = None
				networkSource = serverConf["network"].lower()
			except KeyError as e:
				print(f"ERROR : KeyError due to missing key {e}\
					in YAML configuration file '{yaml_conf_filepath}'")
				sys.exit(1)
			if networkSource=="homeassistant":
				networkUpdater = HomeAssistantAPI(conf)
			else:
				self.logger.critical("OpenHEMSServer() : Unknown network source type '%s'",
					networkSource)
				sys.exit(1)
			network = networkUpdater.getNetwork()
		self.server = OpenHEMSServer(network, serverConf)
		self.webserver = OpenhemsHTTPServer(network.getSchedule())
		network.notify("Start OpenHEMS.")

	def run_management_server(self):
		"""
		Run core server (Smart part) without the webserver part. 
		"""
		self.server.run()

	def run_web_server(self):
		"""
		Run just the webserver part.
		"""
		self.webserver.run()

	def run(self):
		"""
		Run wall OpenHEMS Application
		"""
		t0 = Thread(target=self.run_web_server, args=[])
		t0.start()
		t1 = Thread(target=self.run_management_server, args=[])
		t1.start()
		# t.join()
		# t.run()

def main():
	"""
	Simple function to run wall OpenHEMS Application
	"""
	app = OpenHEMSApplication(yaml_conf)
	app.run()

main()
