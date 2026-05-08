#!/bin/env python

import sys
import os
import logging
from time import sleep

sys.path.append(os.path.dirname(__file__))
import threading
import socket
import json
import threading
import os
import streamlit as st

SOCKET_PATH = "/tmp/openhems.sock"

class UnixSocketServer:
	def __init__(self, schedule, lock, logger=None):
		self.schedule = schedule
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
			if request['action'] == 'get_schedule':
				with self.lock:
					print("Send schedules : ", self.schedule)
					# Sérialiser le schedule dans un format simple
					response = json.dumps(self.schedule)
				conn.send(response.encode('utf-8'))
			elif request['action'] == 'update_device':
				device_id = request['device_id']
				duration = request.get('duration')
				timeout = request.get('timeout')
				with self.lock:
					# Modifier l'objet schedule existant
					self.schedule[device_id].setSchedule(duration, timeout)
				conn.send(b'{"status":"ok"}')
		except Exception as e:
			conn.send(json.dumps({"error": str(e)}).encode('utf-8'))
		finally:
			conn.close()

	@staticmethod
	def send_request(request):
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
		resp = UnixSocketServer.send_request({"action": "get_schedule"})
		return resp

	@staticmethod
	def update_device(device_id, duration, timeout):
		resp = UnixSocketServer.send_request({
			"action": "update_device",
			"device_id": device_id,
			"duration": duration,
			"timeout": timeout
		})
		return resp.get("status") == "ok"