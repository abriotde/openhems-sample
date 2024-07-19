#!/usr/bin/env python3

from web import OpenhemsHTTPServer
from server import OpenHEMSServer
from threading import Thread, Lock
from queue import Queue 

import json
import yaml
from home_assistant_api import HomeAssistantAPI

yaml_conf = "../openhems.yaml"

class OpenHEMSSchedule:
	def __init__(self, name:str, id: str):
		duration = 0
		timeout = 0
		self.name = name
		self.timeout = timeout
		self.duration = duration

	def schedule(self, timeout, duration):
		self.timeout = timeout
		self.duration = duration

	def __json__(self):
		return {"name":self.name, "duration":self.duration, "timeout":self.timeout}


class OpenHEMSApplication:
	def __init__(self, yaml_conf):
		conf = None
		network = None
		serverConf = None
		schedule = {}
		with open(yaml_conf, 'r') as file:
			print("Load YAML configuration from '"+yaml_conf+"'")
			conf = yaml.load(file, Loader=yaml.FullLoader)
			serverConf = conf['server']
			networkUpdater = None
			networkSource = serverConf["network"].lower()
			if networkSource=="homeassistant":
				networkUpdater = HomeAssistantAPI(conf)
			else:
				print("ERROR : OpenHEMSServer() : Unknown network source type '",networkSource,"'")
				exit(1)
			network = networkUpdater.getNetwork()
		for elem in conf["network"]["out"]:
			id = elem["id"]
			node = OpenHEMSSchedule(id, id)
			schedule[id] = node

		self.server = OpenHEMSServer(network, serverConf)
		self.webserver = OpenhemsHTTPServer(schedule)

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
app.run_web_server()

