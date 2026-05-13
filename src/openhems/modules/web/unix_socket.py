#!/bin/env python

import sys
import os
import logging
from time import sleep

from openhems.modules.network.homestate_updater import HomeStateUpdater

sys.path.append(os.path.dirname(__file__))
import threading
import socket
import json
import threading
import os
import streamlit as st
from enum import Enum
import datetime

SOCKET_PATH = "/tmp/openhems.sock"

class UnixSocketServer:
	class Action(Enum):
		GET_SCHEDULE = "get_schedule"
		UPDATE_SCHEDULE = "update_schedule"
		LIST_COMPONENTS = "list_components"

	def __init__(self, schedule, lock, home_state_updater: HomeStateUpdater, logger=None):
		self.schedule = schedule
		self.home_state_updater = home_state_updater
		self.lock = lock
		self.logger = logger or logging.getLogger(__name__)
		self.socket_path = SOCKET_PATH
		self.server = None

	def start(self):
		if os.path.exists(self.socket_path):
			os.unlink(self.socket_path)
		self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.server.bind(self.socket_path)
		self.server.listen(1)
		self.thread = threading.Thread(target=self._accept_connections, daemon=True).start()

	def stop(self):
		self.server.close()
		self.thread.join(5)
		
	def _accept_connections(self):
		while True:
			conn, _ = self.server.accept()
			# threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
			self._handle_client(conn)

	def _handle_client(self, conn):
		try:
			data = conn.recv(4096).decode('utf-8')
			request = json.loads(data)
			action = request.get("action")
			print("UnixSocketServer._handle_client(:", request, ")")
			if action == self.Action.GET_SCHEDULE.value:
				with self.lock:
					# print("Send schedules : ", self.schedule)
					# Sérialiser le schedule dans un format simple
					response = json.dumps(self.schedule)
				conn.send(response.encode('utf-8'))
			elif action == self.Action.UPDATE_SCHEDULE.value:
				id = request['id']
				duration = request.get('duration')
				timeout = request.get('timeout')
				timeout = datetime.datetime.strptime(timeout[0:16], "%Y-%m-%dT%H:%M") if timeout is not None else None
				print("Update schedule for id:", id, "duration:", duration, "timeout:", timeout)
				with self.lock:
					# Modifier l'objet schedule existant
					self.schedule[id].setSchedule(duration, timeout)
				conn.send(b'{"status":"ok"}')
			elif action == self.Action.LIST_COMPONENTS.value:
				components = self.home_state_updater.listComponents()
				response = json.dumps(components)
				conn.send(response.encode('utf-8'))
		except Exception as e:
			print("Error handling socket request:", e, file=sys.stderr)
			conn.send(json.dumps({"error": str(e)}).encode('utf-8'))
		finally:
			conn.close()

	@staticmethod
	def send_request(action, request=None):
		# print(f"send_request({action}, {request})")
		if request is None:
			request = {}
		request["action"] = action.value
		try:
			sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			sock.connect(SOCKET_PATH)
			sock.send(json.dumps(request).encode('utf-8'))
			response = sock.recv(8192).decode('utf-8')
			sock.close()
			return json.loads(response)
		except Exception as e:
			st.error(f"Erreur de communication avec le core : {e}")
			return None

	@staticmethod
	def get_schedule():
		resp = UnixSocketServer.send_request(
			 UnixSocketServer.Action.GET_SCHEDULE
		)
		return resp

	@staticmethod
	def update_schedule(id, duration, timeout):
		data = {
			"id": id,
			"duration": duration,
			"timeout": timeout
		}
		resp = UnixSocketServer.send_request(UnixSocketServer.Action.UPDATE_SCHEDULE, data)
		# print("update_schedule() = ", resp)
		return resp.get("status") == "ok" or resp.get("error")

	@staticmethod
	def get_schedule():
		resp = UnixSocketServer.send_request(
			 UnixSocketServer.Action.GET_SCHEDULE
		)
		return resp

	@staticmethod
	def list_components():
		resp = UnixSocketServer.send_request(
			 UnixSocketServer.Action.LIST_COMPONENTS
		)
		return resp