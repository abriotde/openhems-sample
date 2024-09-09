#!/usr/bin/env python3

import json
import requests
api_key = 'f628f9d85f63d29a7db0f31d2f18a8259fa1cf3afb31c29cfb7a221f' # to be updated
url_sei_corse = 'https://opendata-corse.edf.fr'
api_search = '/api/records/1.0/search'
# define URL and parameters
url = url_sei_corse + api_search
params = {
"apikey": api_key,
"dataset": [
"signal-reseau-corse-recharge-vehicule-electrique "
],
"rows": 288, # get all available entries (288 = 2 days), default is 10
}
# send request
r = requests.get(url,
params=params,
)
r.raise_for_status()
# load JSON response
data = json.loads(r.text)
# extract signal data from JSON response
signal = {record['fields']['date']: record['fields']['signal'] for record in data['records']}
print(signal)
