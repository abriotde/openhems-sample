#!/usr/bin/env python3

import datetime
import time
import pandas as pd
from requests import get, post
import yaml
from home_assistant_api import HomeAssistantAPI
from server import OpenHEMSServer


# api_manager = HomeAssistantAPI("../openhems.yaml")


server = OpenHEMSServer("../openhems.yaml")
server.run()
