#!/usr/bin/env python3
"""
This HomeStateUpdater is based on home-Assistant software. 
It access to this by the API using URL and long_lived_token
"""

import os
import time
import json
import requests
from openhems.modules.network import (
	HomeStateUpdater, HomeStateUpdaterException
)
from openhems.modules.network.feeder import Feeder, SourceFeeder, ConstFeeder
from openhems.modules.util.cast_utility import CastUtililty, CastException
from openhems.modules.util.configuration_manager import ConfigurationManager, ConfigurationException

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
		self.token = os.getenv("SUPERVISOR_TOKEN") # Injected by Supervisor on Home-Assistant OS
		if self.token is None:
			self.apiUrl = conf.get("api.url")
			self.token = conf.get("api.long_lived_token")
		else:
			self.apiUrl = "http://supervisor/core/api"
		self.cachedIds = {}
		# Time to sleep after wrong HomeAssistant call
		self.sleepDurationOnerror = 2
		self.network = None
		self.haElements = None

	def initNetwork(self, network):
		"""
		Get all nodes according to Home-Assistants
		"""
		# print("HomeAssistant.initNetwork()")
		response = self.callAPI("/states")
		self.haElements = {}
		for e in response:
			# print(e)
			entityId = e['entity_id']
			self.haElements[entityId] = e
			# print(entityId, e['state'], e['attributes'])
		self.network = network
		# print("getHANodes() = ", self.haElements)

	def getFeeder(self, value,
			   *, expectedType=None, defaultValue=None, nameid="", node=None
			   ) -> Feeder:
		"""
		Return a feeder considering
		 if the "key" can be a Home-Assistant element id.
		 Otherwise, it consider it as constant.
		"""
		del nameid, node
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

	def registerEntity(self, nameid, typename):
		"""
		Register a Home-Assistant entity for the cache.
		"""
		if self.cachedIds.get(nameid, None) is None:
			self.cachedIds[nameid] = [None, typename]

	def getEntityValue(self, entityId):
		"""
		Return a entity value from its Id (Without cache and not limited to a pre-selected elements)
		"""
		entity = self.cachedIds.get(entityId, None)
		if entity is not None and entity[0] is not None:
			return entity[0]
		response = self.callAPI("/states/"+entityId)
		if response is not None:
			val = response.get("state", None)
			if entity is not None:
				try:
					val = CastUtililty.toType(entity[1], val)
				except CastException as e:
					raise HomeStateUpdaterException(e.message) from e
			return val
		return None

	def updateNetwork(self):
		"""
		Update network, but as we ever know it's architecture,
		 we just have to update few values.
		"""
		super().updateNetwork()
		if len(self.cachedIds) == 0:
			self.logger.warning("HomeAssistantAPI.updateNetwork() : "
				"No entities to update.")
			return True
		response = self.callAPI("/states")
		for e in response:
			# print(e)
			entityId = e['entity_id']
			if entityId in self.cachedIds:
				val = e["state"]
				try:
					value = CastUtililty.toType(self.cachedIds[entityId][1], val)
				except CastException as e:
					raise HomeStateUpdaterException(
						"Home-Assitant entity_id='"+entityId+"' : "+e.message, 0
					) from e
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
		rIsOn = node.isOn()
		if isOn!=rIsOn and node.isSwitchable():
			self.logger.debug("switchOn(%s, %s)", isOn, node)
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
		return rIsOn

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
		data = {
			"entity_id": "device_tracker.2410fpcc5g",
			# "entity_id": "my_direct_message_notifier",
			"message": message,
			"title": "Notification from OpenHEMS."
		}
		self.callAPI("/services/notify/send_message", data=data)

	def getValue(self, entityId, key="state"):
		"""
		Return a entity value from its Id (Without cache and not limited to a pre-selected elements)
		"""
		response = self.callAPI("/states/"+entityId)
		if response is not None:
			val = response.get(key, None)
			return val
		return None

	# pylint: disable=too-many-branches
	def callAPI(self, url: str, data=None):
		"""
		Call Home-Assistant API.
		"""
		headers = {
			"Authorization": "Bearer " + self.token,
			"content-type": "application/json",
		}
		response = None
		self.logger.debug("callAPI(%s)", url)
		try:
			if data is None:
				response = requests.get(self.apiUrl+url,
					headers=headers, timeout=5
					# verify='/etc/letsencrypt/live/openproduct.freeboxos.fr/cert.pem'
				)
			else:
				response = requests.post(self.apiUrl+url,
					headers=headers, json=data, timeout=15
					# verify='/etc/letsencrypt/live/openproduct.freeboxos.fr/cert.pem'
				)
				self.logger.debug("  With data : %s", data)
		except (requests.exceptions.HTTPError,
		  		requests.exceptions.ReadTimeout,
				requests.exceptions.ConnectTimeout) as error:
			msg = ("Unable to access Home Assistance instance, check URL "
		  		f": {self.apiUrl}{url} ({data}) : {error}")
			self.logger.error(msg)
			raise HomeStateUpdaterException(msg) from error
		errMsg = ""
		errCodeMsg = {
			500 : ("Unable to access Home Assistance due to error, "
					f"check devices are up ({url}, {data})"),
			401 : ("Unable to access Home Assistance instance, "
					f"(url={url}, token={self.token}, {data})"
					"If using addon, try setting url and token to 'empty'"),
			404 : f"Invalid URL {self.apiUrl}{url}"
		}
		if response.status_code!=200:
			if response.status_code in errCodeMsg:
				errMsg = errCodeMsg[response.status_code]
			elif response.status_code > 299:
				errMsg = "Request Get Error: {response.status_code}"
			time.sleep(self.sleepDurationOnerror)
			# Maybe is the server overload,
			# overwise it's better to slow down to avoid useless
			# infinite loop on errors.
			self.sleepDurationOnerror = min(self.sleepDurationOnerror*2, 64)
			try:
				errMsg = errMsg.format_map(locals())+" ("+self.apiUrl+url+", "+str(data)+")"
			except KeyError:
				pass
			self.logger.error(errMsg)
			self.logger.debug("With token '%s'", self.token)
			if url!="/services/notify/persistent_notification":
				# To avoid infinite loop : It's url for notify()
				self.notify("Error callAPI() : "
					f"status_code={response.status_code} : {errMsg}")
			if url=="/states":
				raise ConfigurationException(
					"Fail get states of Home-Assistant. "
					"Check the Home-Assistant server is up and check 'Api' tab's parameters."
				)
		else:
			self.sleepDurationOnerror = max(self.sleepDurationOnerror/2, 1)
		try:  # Sometimes when there are connection problems we need to catch empty retrieved json
			return response.json()
		except (json.decoder.JSONDecodeError, requests.exceptions.JSONDecodeError):
			if errMsg=="":
				self.logger.error("Fail parse response '%s'",response)
			return {}
