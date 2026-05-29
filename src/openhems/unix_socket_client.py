#!/bin/env python
"""
Unix socket to comunicate beetwen core OpenHEMS app and the web server.
"""

import sys
import os
import socket
import json
import streamlit as st # pylint: disable=import-error

sys.path.append(os.path.dirname(__file__))
# pylint: disable=wrong-import-position
# from openhems.modules.web.web_streamlit import get_logger
from openhems.unix_socket_action import UnixSocketAction, SOCKET_PATH

# pylint: disable=invalid-name, bad-indentation

class UnixSocketClient:
    """
    Client to send request to the UnixSocketServer.
    """
    def __init__(self, socket_path=SOCKET_PATH):
        # get_logger().info("UnixSocketClient initialized with socket path: " + socket_path)
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
        except (json.JSONDecodeError, ConnectionResetError,
                BrokenPipeError, AttributeError) as e:
            st.error(f"Erreur de communication avec le core : {e}")
            return None
        except FileNotFoundError as e:
            st.error(f"UnixSocketClient.connect : Missing socket '{self.socket_path}'  : {e}")
            return None
        except ConnectionRefusedError as e:
            st.error(f"Socket connection refused to {self.socket_path} : {e}")
            return None

    def get_schedule(self):
        """
        For the client, to ask schedule list.
        """
        resp = self.send_request(
             UnixSocketAction.GET_SCHEDULE
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
        resp = self.send_request(UnixSocketAction.UPDATE_SCHEDULE, data)
        # print("update_schedule() = ", resp)
        return resp.get("status") == "ok" or resp.get("error")

    def list_components(self):
        """
        For the client, to ask the list of existing Home-Assistant available components
          (to limit configuration errors).
        """
        resp = self.send_request(
             UnixSocketAction.LIST_COMPONENTS
        )
        return resp
