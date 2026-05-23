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

sys.path.append(os.path.dirname(__file__))
# pylint: disable=wrong-import-position
from openhems.modules.network.schedule import OpenHEMSSchedule # pylint: disable=E0401
from openhems.modules.network.homestate_updater import HomeStateUpdater
from openhems.unix_socket_action import UnixSocketAction, SOCKET_PATH
from openhems.modules.util.json import json_default
# from openhems.modules.web.web_streamlit import get_logger

# pylint: disable=bad-indentation, invalid-name

class UnixSocketServer:
    """
    Unix socket to comunicate beetwen core app and web server.
    """

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
        self.logger.info(f"UnixSocketServer started on {self.socket_path}")

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
            if action == UnixSocketAction.GET_SCHEDULE.value:
                # print("Send schedules : ", self.schedule)
                # Sérialiser le schedule dans un format simple
                response = json.dumps(self.schedule, default=json_default)
                conn.send(response.encode('utf-8'))
            elif action == UnixSocketAction.UPDATE_SCHEDULE.value:
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
            elif action == UnixSocketAction.LIST_COMPONENTS.value:
                components = self.home_state_updater.listComponents()
                self.logger.info(
                    "UnixSocketServer._handle_client() : "
                    "List components: %s", components
                )
                response = json.dumps(components)
                conn.send(response.encode('utf-8'))
        except (json.JSONDecodeError, ConnectionResetError, BrokenPipeError, AttributeError) as e:
            print("Error handling socket request:", e, file=sys.stderr)
            conn.send(json.dumps({"error": str(e)}).encode('utf-8'))
        finally:
            conn.close()
