#!/usr/bin/env python3
import inspect
import datetime
import time
import pandas as pd
from requests import get, post
import yaml
import logging
from openhems_node import *
from typing import Final

POWER_MARGIN: Final[int] = 10 # Number of cycle we keep history

todays_Date = datetime.date.fromtimestamp(time.time())
date_in_ISOFormat = todays_Date.isoformat()

class HATypeExcetion(Exception):
    def __init__(self, message, defaultValue):
        self.message = message
        self.defaultValue = defaultValue

class HomeAssistantAPI(HomeStateUpdater):

	def __init__(self, conf) -> None:
		self.logger = logging.getLogger(__name__)
		if isinstance(conf, str):
			with open(conf, 'r') as file:
				print("Load YAML configuration from '"+conf+"'")
				conf = yaml.load(file, Loader=yaml.FullLoader)
		self.conf = conf
		apiConf = conf['api']
		self.api_url = apiConf["url"]
		self.token = apiConf["long_lived_token"]
		self.elems = {}
		for id,elem in conf['elems'].items():
			elem['id'] = id
			self.elems[id] = elem
		self._elemsKeysCache = None
		self.cached_ids = dict()
		self.refresh_id = 0

	def getHANodes(self):
		"""
		Get all nodes according to Home-Assistants
		"""
		response = self.callAPI("/states")
		ha_elements = dict()
		for e in response:
			# print(e)
			entity_id = e['entity_id']
			ha_elements[entity_id] = e
			state = e['state']
			attributes = e['attributes']
			# print(entity_id, state, attributes)
		# print("getHANodes() = ", ha_elements)
		return ha_elements

	def getFeeder(self, conf, kkey, ha_elements, params, default_value=None) -> Feeder:
		feeder = None
		if kkey in conf.keys():
			key = conf[kkey]
			if isinstance(key, str) and key in ha_elements.keys():
				self.logger.info("SourceFeeder("+key+")")
				feeder = SourceFeeder(key, self, params)
			else:
				self.logger.info("ConstFeeder("+str(key)+")")
				feeder = ConstFeeder(key)
		elif default_value is None:
			self.logger.critical("HomeAssistantAPI.getFeeder missing configuration key '"+kkey+"'  for network in YAML file ")
			exit(1)
		else:
			feeder = ConstFeeder(default_value)
		return feeder

	def getNetwork(self) -> OpenHEMSNetwork:
		# self.explore()
		self.network = OpenHEMSNetwork(self)
		ha_elements = self.getHANodes()
		network_conf = self.conf["network"]
		# init Feeders
		for e in network_conf["in"]:
			classname = e["class"].lower()
			currentPower = self.getFeeder(e, "currentPower", ha_elements, "int")
			powerMargin = self.getFeeder(e, "powerMargin", ha_elements, "int", POWER_MARGIN)
			maxPower = self.getFeeder(e, "maxPower", ha_elements, "int")
			minPower = self.getFeeder(e, "minPower", ha_elements, "int", 0)
			node = None
			if classname == "publicpowergrid":
				node = PublicPowerGrid(currentPower, maxPower, minPower, powerMargin)
			elif classname == "solarpanel":
				node = SolarPanel(currentPower, maxPower, minPower, powerMargin)
			else:
				self.logger.critical("HomeAssistantAPI.getNetwork : Unknown classname '"+classname+"'")
				exit(1)
			if "id" in e.keys():
				node.id = e["id"]
			# print(node)
			self.network.addNode(node, True)
		i = 0
		for e in network_conf["out"]:
			classname = e["class"].lower()
			node = None
			if "id" in e.keys():
				id = e["id"]
			else:
				id = "node_"+str(i)
				i += 1
			if classname == "switch":
				currentPower = self.getFeeder(e, "currentPower", ha_elements, "int")
				isOn = self.getFeeder(e, "isOn", ha_elements, "bool", True)
				maxPower = self.getFeeder(e, "maxPower", ha_elements, "int", 2000)
				node = OutNode(id, currentPower, maxPower, isOn)
			else:
				self.logger.critical("HomeAssistantAPI.getNetwork : Unknown classname '"+classname+"'")
				exit(1)
			# print(node)
			self.network.addNode(node, False)
		self.network.print(self.logger.info)
		return self.network


	@staticmethod
	def toType(type, value):
		if type=="int":
			if isinstance(value, int):
				return value
			elif isinstance(value, str):
				if value=="unavailable":
					raise HATypeExcetion("WARNING : Unknown value for '"+value+"'", 0)
				else:
					return int(value)
		elif type=="bool":
			if isinstance(value, int):
				return value>0
			elif isinstance(value, str):
				return value.lower() in ["on", "true", "1", "vrai"]
			elif isinstance(value, bool):
				return value
		elif type=="str":
			if isinstance(value, int):
				return str(value)
			elif isinstance(value, str):
				return value
		else:
			print(".toType(",type,",",value,") : Unknwon type")
			exit(1)
		return value
	def updateNetwork(self):
		response = self.callAPI("/states")
		if len(self.cached_ids) == 0:
			self.logger.warning("HomeAssistantAPI.updateNetwork() : No entities to update.")
			return True
		ha_elements = dict()
		for e in response:
			# print(e)
			entity_id = e['entity_id']
			if entity_id in self.cached_ids:
				val = e["state"]
				try:
					value = self.toType(self.cached_ids[entity_id][1], val)
				except HATypeExcetion as e:
					print("ERROR: For '",entity_id," : '",e.message)
					value = e.defaultValue
				self.cached_ids[entity_id][0] = value
				self.logger.info("HomeAssistantAPI.updateNetwork("+entity_id+") = "+str(value))
		self.refresh_id += 1

	def _getElemsKeysCache(self, id, elem=None):
		"""
		@param: If elem is None; get mode; else: insert mode;
		"""
		e = self._elemsKeysCache
		sids = id.split('_')
		length = len(sids)
		for i,sid in enumerate(sids):
			# print("Index:",i,"/",length)
			if not sid in e:
				if elem is None: # Get mode, return last not null elem
					# print("_getElemsKeysCache(",id,") => ", e)
					return e
				e[sid] = dict()
			if i==length-1 and elem is not None: # Do insert for last sub-id
				e[sid] = elem
				# print("_getElemsKeysCache(",id,") => ", self._elemsKeysCache)
				return None
			else:
				e = e[sid]
		# print("_getElemsKeysCache(",id,") => ", e)
		return e

	def createNodeElement(self, elem):
		self.logger.debug("createNodeElement(",elem,")")
		return elem

	def getElemById(self, id:str):
		if id in self.elems:
			return self.elems[id]
		else:
			if self._elemsKeysCache is None:
				self._elemsKeysCache = dict()
				for id,elem in self.elems.items():
					nodeElem = self.createNodeElement(elem)
					self._getElemsKeysCache(id, nodeElem)
				# print("getElemById(",id,") => ",self._elemsKeysCache)
		return self._getElemsKeysCache(id)

	def explore(self):
		response = self.callAPI("/states")
		# elements = dict()
		for e in response:
			# print(e)
			entity_id = e['entity_id']
			state = e['state']
			attributes = e['attributes']
			# print(entity_id, state, attributes)
			domain, elem_id = entity_id.split('.')
			if elem_id.startswith("sm_a047f"):
				print(e)
			# elements[elem_id] = True
			if domain == "sensor":
				if "device_class" in attributes:
					device_class = attributes["device_class"]
					if device_class not in ["timestamp","enum"] and "state_class" in attributes: # Timestamp (solar wakeup), Enum (Tempo day color)
						state_class = attributes["state_class"]
						unit_of_measurement = attributes["unit_of_measurement"]
						elem = self.getElemById(elem_id)
						print(" - ",entity_id,": ",state_class+"/"+device_class+" : ",state,unit_of_measurement, elem)
					# else: print(attributes)
				# else: print(attributes) # how many red day last for Tempo
			elif domain == "update":
				None
			elif domain == "switch":
				if "device_class" in attributes:
					device_class = attributes["device_class"]
					if device_class=="outlet":
						print(domain, elem_id, state)
						self.getElemById(elem_id)
		# print(elements)

	def switchOn(self, isOn, node):
		"""
		return: True if the switch is after on, False else
		"""
		if isOn!=node.isOn():
			if isOn: expectStr = "on"
			else: expectStr = "off"
			entity_id = node._isOn.nameid
			data = {"entity_id": entity_id}
			response = self.callAPI("/services/switch/turn_"+expectStr, data)
			if len(response)==0: # Case there is no change in switch position
				# print("HomeAssistantAPI.switch"+expectStr+"(",entity_id,") : Nothing to do.")
				return isOn
			ok = response[0]["state"]==expectStr
			# print("HomeAssistantAPI.switch"+expectStr+"(",entity_id,") = " ,ok, "(", response[0]["state"], ")")
			return isOn if ok else (not isOn)
		else:
			# print("HomeAssistantAPI.switchOn(",isOn,", ",entity_id,") : Nothing to do.")
			return isOn

	def getServices(self):
		response = self.callAPI("/services")
		for e in response:
			domain = e['domain']
			print(domain)
			if domain=="switch":
				print(e)

	def callAPI(self, url: str, data=None):
		headers = {
			"Authorization": "Bearer " + self.token,
			"content-type": "application/json",
		}
		try:
			if data is None:
				response = get(self.api_url+url, 
					headers=headers,
					# verify='/etc/letsencrypt/live/openproduct.freeboxos.fr/cert.pem'
				)
			else:
				response = post(self.api_url+url, 
					headers=headers, json=data
					# verify='/etc/letsencrypt/live/openproduct.freeboxos.fr/cert.pem'
				)
		except Exception as error:
			self.logger.critical("Unable to access Home Assistance instance, check URL : "+str(error))
			self.logger.critical("HomeAssistantAPI.callAPI("+url+", "+str(data)+")")
			exit(1)
		if response.status_code == 500:
			self.logger.error("Unable to access Home Assistance due to error, check devices are up ("+url+", "+str(data)+")")
		elif response.status_code == 401:
			self.logger.error("Unable to access Home Assistance instance, TOKEN/KEY")
			self.logger.error("If using addon, try setting url and token to 'empty'")
		elif response.status_code > 299:
			self.logger.error("Request Get Error: {response.status_code}")
		"""import bz2 # Uncomment to save a serialized data for tests
		import _pickle as cPickle
		with bz2.BZ2File("data/test_response_get_data_get_method.pbz2", "w") as f: 
		cPickle.dump(response, f)"""
		try:  # Sometimes when there are connection problems we need to catch empty retrieved json
			# print("Response: ",response.json())
			return response.json()
		except IndexError:
			print("The retrieved JSON is empty for day:"+ str(day) +", days_to_retrieve may be larger than the recorded history of sensor:" + var + " (check your recorder settings)")
		# print("HomeAssistantAPI.callAPI(post data=",data,") = ", response)

