#!/usr/bin/env python3
"""
This HomeStateUpdater is based on home-Assistant software. 
It access to this by the API using URL and long_lived_token
"""

import os
import time
import requests
from openhems.modules.network.network import HomeStateUpdater
from openhems.modules.network.feeder import Feeder, SourceFeeder, ConstFeeder
from openhems.modules.util.cast_utility import CastUtililty, CastException
from openhems.modules.util.configuration_manager import ConfigurationManager

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
	def __init__(self, conf:ConfigurationManager) -> None:
		super().__init__(conf)
		self.apiUrl = conf.get("api.url")
		self.token = conf.get("api.long_lived_token")
		self._elemsKeysCache = None
		self.cachedIds = {}
		self.refreshId = 0
		# Time to sleep after wrong HomeAssistant call
		self.sleepDurationOnerror = 2
		self.network = None
		self.haElements = None

	def initNetwork(self):
		"""
		Get all nodes according to Home-Assistants
		"""
		response = self.callAPI("/states")
		self.haElements = {}
		for e in response:
			# print(e)
			entityId = e['entity_id']
			self.haElements[entityId] = e
			# print(entityId, e['state'], e['attributes'])
		# print("getHANodes() = ", self.haElements)

	def getFeeder(self, value, expectedType=None, defaultValue=None) -> Feeder:
		"""
		Return a feeder considering
		 if the "key" can be a Home-Assistant element id.
		 Otherwise, it consider it as constant.
		"""
		feeder = None
		if value is not None:
			if isinstance(value, str) and value in self.haElements:
				self.logger.debug("SourceFeeder(%s)", value)
				feeder = SourceFeeder(value, self, expectedType)
			else:
				# self.logger.debug("ConstFeeder(%s)", value)
				feeder = ConstFeeder(value, None, expectedType)
		elif defaultValue is not None:
			feeder = ConstFeeder(defaultValue, None, expectedType)
		else:
			feeder = None
		return feeder

	def updateNetwork(self):
		"""
		Update network, but as we ever know it's architecture,
		 we just have to update few values.
		"""
		super().updateNetwork()
		response = self.callAPI("/states")
		if len(self.cachedIds) == 0:
			self.logger.warning("HomeAssistantAPI.updateNetwork() : "
				"No entities to update.")
			return True
		for e in response:
			# print(e)
			entityId = e['entity_id']
			if entityId in self.cachedIds:
				val = e["state"]
				try:
					value = CastUtililty.toType(self.cachedIds[entityId][1], val)
				except CastException as e:
					self.logger.error("For '"+entityId+" : '"+e.message)
					self.notify("For '"+entityId+" : '"+e.message)
					value = e.defaultValue
				self.cachedIds[entityId][0] = value
				self.logger.info("HomeAssistantAPI.updateNetwork(%s) = %s", \
					entityId, value)
		return True

	def createNodeElement(self, elem):
		"""
		Create node element
		"""
		self.logger.debug("createNodeElement(%s)", elem)
		return elem

	def switchOn(self, isOn, node):
		"""
		return: True if the switch is after on, False else
		"""
		if isOn!=node.isOn() and node.isSwitchable():
			expectStr = "on" if isOn else "off"
			# pylint: disable=protected-access
			entityId = node._isOn.nameid # (Should do in an other way?)
			response = self.callAPI(
				"/services/switch/turn_"+expectStr,
				{"entity_id": entityId}
			)
			if len(response)==0: # Case there is no change in switch position
				# print("HomeAssistantAPI.switch"+expectStr+"(",entityId,") : Nothing to do.")
				return isOn
			state = response[0]["state"]
			ok = state==expectStr
			# print("HomeAssistantAPI.switch"+expectStr+"(",entityId,") \
			#	= " ,ok, "(", response[0]["state"], ")")
			return isOn if ok else (not isOn)
		# print("HomeAssistantAPI.switchOn(",isOn,", ",entityId,") :
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
				response = requests.get(self.apiUrl+url,
					headers=headers, timeout=5
					# verify='/etc/letsencrypt/live/openproduct.freeboxos.fr/cert.pem'
				)
			else:
				response = requests.post(self.apiUrl+url,
					headers=headers, json=data, timeout=5
					# verify='/etc/letsencrypt/live/openproduct.freeboxos.fr/cert.pem'
				)
		except Exception as error:
			self.logger.critical("Unable to access Home Assistance instance, check URL : %s", error)
			self.logger.critical("HomeAssistantAPI.callAPI(%s, %s)", url, str(data))
			os._exit(1)
		errMsg = ""
		errCodeMsg = {
			500 : ("Unable to access Home Assistance due to error, "
					"check devices are up ({url}, {data})"),
			401 : ("Unable to access Home Assistance instance, "
					"(url={url}, token={self.token}, {data})"
					"If using addon, try setting url and token to 'empty'"),
			404 : "Invalid URL {self.apiUrl}{url}"
		}
		if response.status_code in errCodeMsg:
			errMsg = errCodeMsg[response.status_code]
		elif response.status_code > 299:
			errMsg = "Request Get Error: {response.status_code}"
		if errMsg!="":
			time.sleep(self.sleepDurationOnerror)
			# Maybe is the server overload,
			# overwise it's better to slow down to avoid useless
			# infinite loop on errors.
			self.sleepDurationOnerror = min(self.sleepDurationOnerror*2, 64)
			errMsg = errMsg.format_map(locals())+" ("+url+", "+str(data)+")"
			self.logger.error(errMsg)
			if url!="/services/notify/persistent_notification":
				# To avoid infinite loop : It's url for notify()
				self.notify(f"Error callAPI() : \
					status_code={response.status_code} : {errMsg}")
		else:
			if self.sleepDurationOnerror>2:
				self.sleepDurationOnerror /= 2
		try:  # Sometimes when there are connection problems we need to catch empty retrieved json
			return response.json()
		except Exception:
			if errMsg=="":
				self.logger.error("Fail parse response '%s'",response)
			return {}
