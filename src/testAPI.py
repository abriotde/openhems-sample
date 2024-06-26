#!/usr/bin/env python3

import datetime
import time
import pandas as pd
from requests import get, post
import yaml
from home_assistant_api import HomeAssistantAPI


api_manager = HomeAssistantAPI("../openhems.yaml", 30)
# api_manager.getServices()
# api_manager.getStates()
