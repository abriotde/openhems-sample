#!/usr/bin/env python3
"""
This is the OpenHEMS module. It aims to give
Home Energy Management Automating System on house. 
It is a back application of Home-Assistant.
More informations on https://openhomesystem.com/
"""

import sys
import logging
from threading import Thread
import argparse
import threading
import traceback
from pathlib import Path

ROOT_PATH = Path(__file__).parents[3]
from openhems.modules.util.project_configuration import ProjectConfiguration
openhemsPath = Path(__file__).parents[1]
sys.path.append(str(openhemsPath))
# pylint: disable=wrong-import-position
from openhems.modules.network.driver.home_assistant_api import HomeAssistantAPI
from openhems.modules.network.driver.fake_network import FakeNetwork
from openhems.modules.network import Network, HomeStateUpdaterException
from openhems.unix_socket_server import UnixSocketServer
from openhems.modules.web import OpenhemsHTTPServer
from openhems.modules.util import (
	ConfigurationManager, ConfigurationException,
	CastUtililty, CastException, getLogger
)
from openhems.server import OpenHEMSServer


class OpenHEMSApplication:
	"""
	This class is the main class to manage OpenHEMS as independant application.
	"""

	def getNetworkFromConfiguration(self, logger, configurator:ConfigurationManager):
		"""
		Method to instantiate a network from a ConfigurationManager 
		"""
		networkSource = configurator.get("server.network")
		if networkSource=="homeassistant":
			logger.info("Network: HomeAssistantAPI")
			networkUpdater = HomeAssistantAPI(configurator)
		elif networkSource=="fake":
			logger.info("Network: FakeNetwork")
			networkUpdater = FakeNetwork(configurator)
		else:
			raise ConfigurationException(f"Invalid server.network configuration '{networkSource}'")
		network = Network(logger, networkUpdater, configurator.get("network.nodes"))
		return network

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
			else: print("No '",str(path),"'")
		configurator.completeWithDefaults()
		return configurator

	def __init__(self, yamlConfFilepath:str, *, port=0, logfilepath='', inDocker=False):
		# Temporary logger
		#pylint: disable=too-many-locals
		self.logger = logging.getLogger(__name__)
		# Keep warnings for tests (self.server can be None if it raise Exception).
		self.warnings = []
		network = None
		schedule = []
		configurator = ConfigurationManager(self.logger)
		self.configurator = configurator
		try:
			configurator = self.loadYamlConfiguration(configurator, yamlConfFilepath)
		except ConfigurationException as e:
			self.warnings.append(str(e))
		loglevel = configurator.get("server.loglevel")
		logformat = configurator.get("server.logformat")
		logfile = logfilepath if logfilepath!='' else configurator.get("server.logfile")
		self.logger = getLogger(loglevel, logformat, logfile, inDocker)
		self.logger.info("Load YAML configuration from '%s'.",yamlConfFilepath)
		self.server:OpenHEMSServer = None
		# pylint: disable=broad-exception-caught
		try:
			network = self.getNetworkFromConfiguration(self.logger, configurator)
			self.server = OpenHEMSServer(self.logger, network, configurator)
			self.warnings = self.warnings + self.server.getWarningMessages()
			schedule = self.server.getSchedule()
		except (HomeStateUpdaterException, CastException, ConfigurationException) as e:
			# at least HomeStateUpdaterException, CastException, ConfigurationException
			# Avoid to raise exception, prefer using warnings to have all services working
			#  (at least Web IHM).
			errclass = type(e).__name__
			trace = ''.join(traceback.TracebackException.from_exception(e).format())
			message = f"Error during network initialization : {errclass} : {e.message} : {trace}"
			self.logger.error(message)
			self.warnings.append(message)
		for warning in self.warnings:
			self.logger.error(warning)
		port = port if port>0 else configurator.get("server.port")
		port = CastUtililty.toTypeInt(port)
		root = configurator.get("server.htmlRoot")
		inDocker = inDocker or configurator.get("server.inDocker", "bool")
		self.webserver = OpenhemsHTTPServer(self.logger, schedule, self.warnings,
			port=port, html_root=root, in_docker=inDocker, configurator=configurator)
		if network is not None:
			self.logger.info("OpenHEMS loaded.")
			network.notify("Start OpenHEMS.")

	def runManagementServer(self, event:threading.Event=None):
		"""
		Run core server (Smart part) without the webserver part. 
		"""

		if self.server is not None:
			schedule = self.server.getSchedule()
			network = self.server.getNetwork()
		else: # Create a UnixSocketServer even if there is no core server.
			# In order to allow webserver to start and display error messages / reconfigure server.
			schedule = {}
			network = FakeNetwork(ProjectConfiguration())
		try:
			socket = UnixSocketServer(
				schedule,
				network,
				socket_path=self.configurator.get("server.socketpath"),
				logger=self.logger
			)
			socket.start()
		except Exception as e: # pylint: disable=broad-exception-caught
			self.logger.error("Error occurred while starting management server: %s", e)
		if event:
			event.set()

		if self.server is not None:
			# server.run() is infinite loop (never give hand back)
			try:
				self.server.run()
			except Exception as e: # pylint: disable=broad-exception-caught
				self.logger.error("Error occurred while running management server: %s", e)
		else:
			self.logger.error(
				"Core server cannot start because of "
				"previous errors during initialization."
			)

	def runWebServer(self):
		"""
		Run just the webserver part.
		"""
		self.webserver.run()

	def run(self):
		"""
		Run wall OpenHEMS Application
		"""
		event = threading.Event()
		t1 = Thread(target=self.runManagementServer, args=[event])
		t1.start()
		# Wait UnixSocketServer started (before web server try listen to it)
		event.wait()
		t0 = Thread(target=self.runWebServer, args=[])
		t0.start()
		# t.join()
		# t.run()

def main():
	"""
	Simple function to run wall OpenHEMS Application. Parse commandline:
	* -p/--port : Set the HTML listening port
	* -c/--conf : Set the YAML configuration file (default is ../../config/openhems.yaml)
	* -l/--logfile : Set the log file path.
	* -h/--help : Print help
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
