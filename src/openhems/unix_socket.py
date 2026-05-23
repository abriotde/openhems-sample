#!/bin/env python
"""
Unix socket to comunicate beetwen core OpenHEMS app and the web server.
"""

import sys
import os
import logging
import datetime
import threading
import socket
import json
from enum import Enum
import streamlit as st # pylint: disable=E0401

sys.path.append(os.path.dirname(__file__))
# pylint: disable=wrong-import-position
from openhems.modules.network.schedule import OpenHEMSSchedule # pylint: disable=E0401
from openhems.modules.network.homestate_updater import HomeStateUpdater

SOCKET_PATH = "/tmp/openhems.sock"

# pylint: disable=invalid-name, bad-indentation # Until full migration to snake_case
def json_default(obj):
    """
    Override JSON serializer for objects to use __json__ method.
    """
    if hasattr(obj, "__json__"):
        return obj.__json__()
    # Optionnel : gérer d'autres types non sérialisables
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

class UnixSocketServer:
    """
    Unix socket to comunicate beetwen core app and web server.
    """
    class Action(Enum):
        """
        List available actions on this socket
        """
        GET_SCHEDULE = "get_schedule"
        UPDATE_SCHEDULE = "update_schedule"
        LIST_COMPONENTS = "list_components"

    def __init__(self, schedule: list[OpenHEMSSchedule],
                  network: HomeStateUpdater, socket_path=SOCKET_PATH, logger=None):
        self.schedule = schedule
        self.home_state_updater = network
        self.logger = logger or logging.getLogger(__name__)
        self.socket_path = socket_path
        self.server = None
        self.thread = None

    def start(self):
        """
        Start the unix socket server.
        """
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.socket_path)
        self.server.listen(1)
        self.thread = threading.Thread(target=self._accept_connections, daemon=True)
        self.thread.start()

    def stop(self):
        """
        Stop the unix socket server.
        """
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
                # print("Send schedules : ", self.schedule)
                # Sérialiser le schedule dans un format simple
                response = json.dumps(self.schedule, default=json_default)
                conn.send(response.encode('utf-8'))
            elif action == self.Action.UPDATE_SCHEDULE.value:
                request_id = request['id']
                duration = request.get('duration')
                timeout = request.get('timeout')
                if timeout is not None:
                    timeout = datetime.datetime.strptime(
                        timeout[0:16].replace("T", " "),
                        "%Y-%m-%d %H:%M"
                    )
                print("Update schedule for id:", request_id,
                      "duration:", duration, "timeout:", timeout)
                # Modifier l'objet schedule existant
                self.schedule[request_id].set_schedule(duration, timeout)
                conn.send(b'{"status":"ok"}')
            elif action == self.Action.LIST_COMPONENTS.value:
                components = self.home_state_updater.listComponents()
                response = json.dumps(components)
                conn.send(response.encode('utf-8'))
        except (json.JSONDecodeError, ConnectionResetError, BrokenPipeError, AttributeError) as e:
            print("Error handling socket request:", e, file=sys.stderr)
            conn.send(json.dumps({"error": str(e)}).encode('utf-8'))
        finally:
            conn.close()

class UnixSocketClient:
    """
    Client to send request to the UnixSocketServer.
    """
    def __init__(self, socket_path=SOCKET_PATH):
        self.socket_path = socket_path

    def send_request(self, action, request=None):
        """
        Used by client to send a correct request to this unix socket server 
        """
        # print(f"send_request({action}, {request})")
        if request is None:
            request = {}
        request["action"] = action.value
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            sock.send(json.dumps(request).encode('utf-8'))
            response = sock.recv(8192).decode('utf-8')
            sock.close()
            return json.loads(response)
        except (json.JSONDecodeError, ConnectionResetError, BrokenPipeError, AttributeError) as e:
            st.error(f"Erreur de communication avec le core : {e}")
            return None

    def get_schedule(self):
        """
        For the client, to ask schedule list.
        """
        resp = self.send_request(
             UnixSocketServer.Action.GET_SCHEDULE
        )
        return resp

    def update_schedule(self, schedule_id, duration, timeout):
        """
        For the client, to update a schedule for a device.
        """
        data = {
            "id": schedule_id,
            "duration": duration,
            "timeout": timeout
        }
        resp = self.send_request(UnixSocketServer.Action.UPDATE_SCHEDULE, data)
        # print("update_schedule() = ", resp)
        return resp.get("status") == "ok" or resp.get("error")

    def list_components(self):
        """
        For the client, to ask the list of existing Home-Assistant available components
          (to limit configuration errors).
        """
        resp = self.send_request(
             UnixSocketServer.Action.LIST_COMPONENTS
        )
        return resp
