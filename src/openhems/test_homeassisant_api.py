#!/usr/bin/env python3
"""
This is the OpenHEMS module. It aims to give
 Home Energy Management Automating System on house. 
 It is a back application of Home-Assistant.
More informations on https://openhomesystem.com/
"""

from pathlib import Path
from requests import get
import json
import yaml

yamlConfig = Path(__file__).parents[2] / "config/openhems.yaml"

with yamlConfig.open('r', encoding="utf-8") as file:
	print("Load YAML configuration from ", yamlConfig)
	dictConfig = yaml.load(file, Loader=yaml.FullLoader)
	long_lived_token = dictConfig['api']['long_lived_token']
	url = dictConfig['api']['url']+"/states"
	headers = {
		"Authorization": "Bearer "+long_lived_token,
		"content-type": "application/json",
	}
	print("GET "+url)
	response = get(url, headers=headers)
	if response.status_code==200:
		json_object = json.loads(response.text)
		print(json.dumps(json_object, indent=1))
	else:
		print("> ", response.status_code, "=>", response.text)
