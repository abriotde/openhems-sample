#!/usr/bin/env python3
"""
This HomeStateUpdater is based on home-Assistant software. 
It access to this by the API using URL and long_lived_token
"""

import os
import logging
import datetime
import time
import requests
import yaml
from openhems.modules.network.network import OpenHEMSNetwork, HomeStateUpdater
from openhems.modules.network.network import POWER_MARGIN
from openhems.modules.network.feeder import Feeder, SourceFeeder, ConstFeeder
from openhems.modules.network.node import PublicPowerGrid, SolarPanel, Battery, OutNode

todays_Date = datetime.date.fromtimestamp(time.time())
date_in_ISOFormat = todays_Date.isoformat()

class HATypeExcetion(Exception):
	"""
	Custom Home-Assitant excepton to be captured.
	"""
	def __init__(self, message, defaultValue):
		self.message = message
		self.defaultValue = defaultValue

class HomeAssistantAPI(HomeStateUpdater):
	"""
	This HomeStateUpdater is based on home-Assistant software. 
	It access to this by the API using URL and long_lived_token
	"""
	def __init__(self, conf) -> None:
		self.logger = logging.getLogger(__name__)
		if isinstance(conf, str):
			with open(conf, 'r', encoding="utf-8") as file:
				print("Load YAML configuration from '"+conf+"'")
				conf = yaml.load(file, Loader=yaml.FullLoader)
		self.conf = conf
		apiConf = conf['api']
		self.api_url = apiConf["url"]
		self.token = apiConf["long_lived_token"]
		self.elems = {}
		for HAid,elem in conf['elems'].items():
			elem['id'] = HAid
			self.elems[HAid] = elem
		self._elemsKeysCache = None
		self.cached_ids = {}
		self.refresh_id = 0
		# Time to sleep after wrong HomeAssistant call
		self.sleep_duration_onerror = 2
		self.network = None

	def getHANodes(self):
		"""
		Get all nodes according to Home-Assistants
		"""
		response = self.callAPI("/states")
		ha_elements = {}
		for e in response:
			# print(e)
			entity_id = e['entity_id']
			ha_elements[entity_id] = e
			# print(entity_id, e['state'], e['attributes'])
		# print("getHANodes() = ", ha_elements)
		return ha_elements

	def getFeeder(self, conf, kkey, ha_elements, params, default_value=None) -> Feeder:
		"""
		Return a feeder considering
		 if the "kkey" can be a Home-Assistant element id.
		 Otherwise, it consider it as constant.
		"""
		feeder = None
		if kkey in conf.keys():
			key = conf[kkey]
			if isinstance(key, str) and key in ha_elements.keys():
				self.logger.info("SourceFeeder({key})")
				feeder = SourceFeeder(key, self, params)
			else:
				self.logger.info("ConstFeeder({key})")
				feeder = ConstFeeder(key)
		elif default_value is None:
			self.logger.critical("HomeAssistantAPI.getFeeder missing\
				 configuration key '{kkey}'  for network in YAML file ")
			os._exit(1)
		else:
			feeder = ConstFeeder(default_value)
		return feeder

	def getNetworkIn(self, network_conf, ha_elements):
		"""
		Initialyze "in" network part.
		"""
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
			elif classname == "battery":
				lowLevel = self.getFeeder(e, "lowLevel",
					ha_elements, "int", POWER_MARGIN)
				hightLevel = self.getFeeder(e, "hightLevel",
					ha_elements, "int", POWER_MARGIN)
				capacity = self.getFeeder(e, "capaciity",
					ha_elements, "int", POWER_MARGIN)
				currentLevel = self.getFeeder(e, "level", ha_elements, "int", 0)
				node = Battery(currentPower, maxPower, powerMargin, capacity,
					currentLevel ,minPower=minPower, lowLevel=lowLevel,
					hightLevel=hightLevel)
			else:
				self.logger.critical("HomeAssistantAPI.getNetwork : "
					"Unknown classname '{classname}'")
				os._exit(1)
			if "id" in e.keys():
				node.id = e["id"]
			# print(node)
			self.network.addNode(node)

	def getNetworkOut(self, network_conf, ha_elements):
		"""
		Initialyze "out" network part.
		"""
		i = 0
		for e in network_conf["out"]:
			classname = e["class"].lower()
			node = None
			if "id" in e.keys():
				HAid = e["id"]
			else:
				HAid = "node_"+str(i)
				i += 1
			if classname == "switch":
				currentPower = self.getFeeder(e, "currentPower", ha_elements, "int")
				isOn = self.getFeeder(e, "isOn", ha_elements, "bool", True)
				maxPower = self.getFeeder(e, "maxPower", ha_elements, "int", 2000)
				node = OutNode(HAid, currentPower, maxPower, isOn)
			else:
				self.logger.critical("HomeAssistantAPI.getNetwork : "
					"Unknown classname '{classname}'")
				os._exit(1)
			# print(node)
			self.network.addNode(node)

	def getNetwork(self) -> OpenHEMSNetwork:
		"""
		Explore the home device network available with Home-Assistant.
		"""
		# self.explore()
		self.network = OpenHEMSNetwork(self)
		ha_elements = self.getHANodes()
		network_conf = self.conf["network"]
		self.getNetworkIn(network_conf, ha_elements)
		self.getNetworkOut(network_conf, ha_elements)
		self.network.print(self.logger.info)
		return self.network

	@staticmethod
	def toTypeInt(value):
		"""
		Convert to type integer
		"""
		retValue = None
		if isinstance(value, int):
			retValue = value
		elif isinstance(value, str):
			if value=="unavailable":
				raise HATypeExcetion("WARNING : Unknown value for '"+value+"'", 0)
			retValue = int(value)
		return retValue
	@staticmethod
	def toTypeBool(value):
		"""
		Convert to type boolean
		"""
		retValue = None
		if isinstance(value, int):
			retValue = value>0
		elif isinstance(value, str):
			retValue = value.lower() in ["on", "true", "1", "vrai"]
		elif isinstance(value, bool):
			retValue = value
		return retValue
	@staticmethod
	def toTypeStr(value):
		"""
		Convert to type string
		"""
		if isinstance(value, int):
			retValue = str(value)
		elif isinstance(value, str):
			retValue = value
		else:
			retValue = str(value)
		return retValue

	@staticmethod
	def toType(destType, value):
		"""
		With Home-Assitant API we get all as string.
		 If it's power or other int value, we need to convert it.
		 We need to manage some incorrect value due to errors.
		"""
		retValue = None
		if destType=="int":
			retValue = HomeAssistantAPI.toTypeInt(value)
		elif destType=="bool":
			retValue = HomeAssistantAPI.toTypeBool(value)
		elif destType=="str":
			retValue = HomeAssistantAPI.toTypeStr(value)
		else:
			print(".toType(",destType,",",value,") : Unknwon type")
			os._exit(1)
		return retValue

	def updateNetwork(self):
		"""
		Update network, but as we ever know it's architecture,
		 we just have to update few values.
		"""
		response = self.callAPI("/states")
		if len(self.cached_ids) == 0:
			self.logger.warning("HomeAssistantAPI.updateNetwork() : "
				"No entities to update.")
			return True
		for e in response:
			# print(e)
			entity_id = e['entity_id']
			if entity_id in self.cached_ids:
				val = e["state"]
				try:
					value = self.toType(self.cached_ids[entity_id][1], val)
				except HATypeExcetion as e:
					self.logger.error("For '"+entity_id+" : '"+e.message)
					self.notify("For '"+entity_id+" : '"+e.message)
					value = e.defaultValue
				self.cached_ids[entity_id][0] = value
				self.logger.info("HomeAssistantAPI.updateNetwork({entity_id}) = {value}")
		self.refresh_id += 1
		return True

	def _getElemsKeysCache(self, HAid, elem=None):
		"""
		@param: If elem is None; get mode; else: insert mode;
		"""
		e = self._elemsKeysCache
		sids = HAid.split('_')
		length = len(sids)
		for i,sid in enumerate(sids):
			# print("Index:",i,"/",length)
			if not sid in e:
				if elem is None: # Get mode, return last not null elem
					# print("_getElemsKeysCache(",HAid,") => ", e)
					return e
				e[sid] = {}
			if i==length-1 and elem is not None: # Do insert for last sub-id
				e[sid] = elem
				# print("_getElemsKeysCache(",HAid,") => ", self._elemsKeysCache)
				return None
			e = e[sid]
		# print("_getElemsKeysCache(",HAid,") => ", e)
		return e

	def createNodeElement(self, elem):
		"""
		Create node element
		"""
		self.logger.debug("createNodeElement(%s)", elem)
		return elem

	def getElemById(self, HAid:str):
		"""
		Return the node element eer explored by id
		"""
		if HAid in self.elems:
			return self.elems[HAid]
		elemId = None
		if self._elemsKeysCache is None:
			self._elemsKeysCache = {}
			for elemId,elem in self.elems.items():
				nodeElem = self.createNodeElement(elem)
				self._getElemsKeysCache(elemId, nodeElem)
		# print("getElemById(",elemId,") => ",self._elemsKeysCache)
		return self._getElemsKeysCache(elemId)

	def explore(self):
		"""
		@useless? Used for debug.
		Explore the home device network available with Home-Assistant.
		"""
		response = self.callAPI("/states")
		# elements = {}
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
					# Timestamp (solar wakeup), Enum (Tempo day color)
					if device_class not in ["timestamp","enum"] \
							and "state_class" in attributes:
						state_class = attributes["state_class"]
						unit_of_measurement = attributes["unit_of_measurement"]
						elem = self.getElemById(elem_id)
						print(" - ",entity_id,": ",state_class+"/"+device_class+" : ",state,unit_of_measurement, elem)
					# else: print(attributes)
				# else: print(attributes) # how many red day last for Tempo
			elif domain == "update":
				pass
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
		if isOn!=node.isOn() and node.isSwitchable():
			expectStr = "on" if isOn else "off"
			# pylint: disable=protected-access
			entity_id = node._isOn.nameid # (Should do in an other way?)
			data = {"entity_id": entity_id}
			response = self.callAPI("/services/switch/turn_"+expectStr, data)
			if len(response)==0: # Case there is no change in switch position
				# print("HomeAssistantAPI.switch"+expectStr+"(",entity_id,") : Nothing to do.")
				return isOn
			state = response[0]["state"]
			ok = state==expectStr
			# print("HomeAssistantAPI.switch"+expectStr+"(",entity_id,") \
			#	= " ,ok, "(", response[0]["state"], ")")
			return isOn if ok else (not isOn)
		# print("HomeAssistantAPI.switchOn(",isOn,", ",entity_id,") :
		# Nothing to do.")
		return node.isOn()

	def getServices(self):
		"""
		Print Home-Assistant services list.
		"""
		response = self.callAPI("/services")
		for e in response:
			domain = e['domain']
			print(domain)
			if domain=="switch":
				print(e)

	def notify(self, message):
		"""
		Send a notification to Home-Assistant. The end-user will see it.
		"""
		data = {
			"message":message,
			"title":"Notification from OpenHEMS."
		}
		self.callAPI("/services/notify/persistent_notification", data=data)

	def callAPI(self, url: str, data=None):
		"""
		Call Home-Assistant API.
		"""
		headers = {
			"Authorization": "Bearer " + self.token,
			"content-type": "application/json",
		}
		response = None
		# pylint: disable=broad-exception-caught
		try:
			if data is None:
				response = requests.get(self.api_url+url,
					headers=headers, timeout=5
					# verify='/etc/letsencrypt/live/openproduct.freeboxos.fr/cert.pem'
				)
			else:
				response = requests.post(self.api_url+url,
					headers=headers, json=data, timeout=5
					# verify='/etc/letsencrypt/live/openproduct.freeboxos.fr/cert.pem'
				)
		except Exception as error:
			self.logger.critical("Unable to access Home Assistance instance, check URL : %s", error)
			self.logger.critical("HomeAssistantAPI.callAPI({url}, {data})")
			os._exit(1)
		errMsg = ""
		err_code_msg = {
			500 : ("Unable to access Home Assistance due to error, "
					"check devices are up ({url}, {data})"),
			401 : ("Unable to access Home Assistance instance, "
					"(url={url}, token={self.token}, {data})"
					"If using addon, try setting url and token to 'empty'"),
			404 : "Invalid URL {self.api_url}{url}"
		}
		if response.status_code in err_code_msg:
			errMsg = err_code_msg[response.status_code]
		elif response.status_code > 299:
			errMsg = "Request Get Error: {response.status_code}"
		if errMsg!="":
			time.sleep(self.sleep_duration_onerror)
			# Maybe is the server overload,
			# overwise it's better to slow down to avoid useless
			# infinite loop on errors.
			sleep_duration_onerror = min(sleep_duration_onerror*2, 64)
			errMsg += " ("+url+", "+str(data)+")"
			self.logger.error(errMsg)
			if url!="/services/notify/persistent_notification":
				# To avoid infinite loop : It's url for notify()
				self.notify("Error callAPI() : status_code="
					"{response.status_code} : {errMsg}")
		else:
			if self.sleep_duration_onerror>2:
				self.sleep_duration_onerror /= 2
		try:  # Sometimes when there are connection problems we need to catch empty retrieved json
			return response.json()
		except Exception:
			if errMsg=="":
				self.logger.error("Fail parse response '%s'",response)
			return {}
