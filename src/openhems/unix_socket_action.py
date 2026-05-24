"""
List available "actions" for UnixSocket.
"""

from enum import Enum

# pylint: disable=bad-indentation
class UnixSocketAction(Enum):
    """
    List available actions on this socket
    """
    GET_SCHEDULE = "get_schedule"
    UPDATE_SCHEDULE = "update_schedule"
    LIST_COMPONENTS = "list_components"

SOCKET_PATH = "/tmp/openhems.sock"
