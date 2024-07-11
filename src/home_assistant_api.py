#!/usr/bin/env python3

import datetime
import time
import pandas as pd
from requests import get, post
import yaml
from openhems_node import OpenHEMSNode, HomeStateUpdater, OpenHEMSNetwork


todays_Date = datetime.date.fromtimestamp(time.time())
date_in_ISOFormat = todays_Date.isoformat()


class HomeAssistantAPI(HomeStateUpdater):

	def __init__(self, conf) -> None:
		if isinstance(conf, str):
			with open(conf, 'r') as file:
				print("Load YAML configuration from '"+conf+"'")
				conf = yaml.load(file, Loader=yaml.FullLoader)
		apiConf = conf['api']
		self.api_url = apiConf["url"]
		self.token = apiConf["long_lived_token"]
		self.elems = {}
		for id,elem in conf['elems'].items():
			elem['id'] = id
			self.elems[id] = elem
		self._elemsKeysCache = None

	def getNetwork(self) -> OpenHEMSNetwork:
		self.network = OpenHEMSNetwork(self)
		self.initStates()
		print("HomeAssistantAPI.getNetwork() : To implement in sub-class")
		return self.network

	def updateNetwork(self):
		print("HomeAssistantAPI.updateNetwork() : To implement in sub-class")

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
		print("createNodeElement(",elem,")")
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

	def initStates(self):
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
	# TODO
	def updateStates(self):
		response = self.callAPI("/states")
		print("TODO...")
		exit(0)

	def getServices(self):
		response = self.callAPI("/services")
		for e in response:
			domain = e['domain']
			print(domain)
			if domain=="switch":
				print(e)

	def callAPI(self, url: str):
		headers = {
			"Authorization": "Bearer " + self.token,
			"content-type": "application/json",
		}
		try:
			response = get(self.api_url+url, 
				headers=headers,
				# verify='/etc/letsencrypt/live/openproduct.freeboxos.fr/cert.pem'
			)
		except Exception as error:
			print(
				"Unable to access Home Assistance instance, check URL : ", error
			)
			exit(1)
		else:
			if response.status_code == 401:
				print(
					"Unable to access Home Assistance instance, TOKEN/KEY"
				)
				print(
					"If using addon, try setting url and token to 'empty'"
				)
			if response.status_code > 299:
				print("Request Get Error: {response.status_code}")
		"""import bz2 # Uncomment to save a serialized data for tests
		import _pickle as cPickle
		with bz2.BZ2File("data/test_response_get_data_get_method.pbz2", "w") as f: 
			cPickle.dump(response, f)"""
		try:  # Sometimes when there are connection problems we need to catch empty retrieved json
			# print("Response: ",response.json())
			return response.json()
		except IndexError:
			print("The retrieved JSON is empty for day:"+ str(day) +", days_to_retrieve may be larger than the recorded history of sensor:" + var + " (check your recorder settings)")

