"""
A Home Energy Management System based on Home-Assistant

Module to easily launch customized OpenHEMS Application.
"""

from .modules import *
from .main import OpenHEMSApplication, main
from .server import OpenHEMSServer

# __version__ = "0.1.12"
# __display_version__ = __version__  # used for command line version
