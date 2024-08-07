#!/usr/bin/env python3

from web import OpenhemsHTTPServer
from server import OpenHEMSServer
from threading import Thread

import logging
import os
import json
import yaml
from home_assistant_api import HomeAssistantAPI

yaml_conf = os.path.dirname(__file__)+"/../openhems.yaml"
LOGFORMAT = '%(levelname)s : %(asctime)s : %(message)s'
LOGFILE = '/var/log/openhems.log'

class OpenHEMSApplication:
	def __init__(self, yaml_conf):
		conf = None
		network = None
		serverConf = None
		schedule = {}
		with open(yaml_conf, 'r') as file:
			print("Load YAML configuration from '"+yaml_conf+"'")
			conf = yaml.load(file, Loader=yaml.FullLoader)
			try:
				serverConf = conf['server']
				loglevel = serverConf.get("loglevel", "info")
				logformat = serverConf.get("logformat", LOGFORMAT)
				logfile = serverConf.get("logfile", LOGFILE)
				if loglevel=="debug":
					level=logging.DEBUG
				elif loglevel=="warn" or loglevel=="warning":
					level=logging.WARNING
				elif loglevel=="error":
					level=logging.ERROR
				elif loglevel=="critical" or loglevel=="no":
					level=logging.CRITICAL
				else: # if loglevel=="info":
					level=logging.INFO
				logging.basicConfig(filename=logfile, level=level, format=logformat)
				self.logger = logging.getLogger(__name__)
				self.logger.info("Load YAML configuration from '"+yaml_conf+"'")
				networkUpdater = None
				networkSource = serverConf["network"].lower()
			except KeyError as e:
				print("ERROR : KeyError due to missing key "+str(e)+" in YAML configuration file '"+yaml_conf+"'")
				exit(1)
			if networkSource=="homeassistant":
				networkUpdater = HomeAssistantAPI(conf)
			else:
				self.logger.critical("OpenHEMSServer() : Unknown network source type '"+networkSource+"'")
				exit(1)
			network = networkUpdater.getNetwork()
		self.server = OpenHEMSServer(network, serverConf)
		self.webserver = OpenhemsHTTPServer(network.getSchedule())

	def run_management_server(self):
		self.server.run()

	def run_web_server(self):
		self.webserver.run()

	def run(self):
		t0 = Thread(target=self.run_web_server, args=[])
		t0.start()
		t1 = Thread(target=self.run_management_server, args=[])
		t1.start()
		# t.join()
		# t.run()

app = OpenHEMSApplication(yaml_conf)
app.run()

