#!/usr/bin/env python3

import json
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
from json import JSONEncoder

class OpenHEMSJSONEncoder(JSONEncoder):
	def default(self, o):
		return o.__dict__

openHEMSContext = None

@view_config(
    route_name='panel',
    renderer='templates/panel.jinja2'
)
def panel(request):
    return { "nodes": json.dumps(OpenHEMSJSONEncoder().encode(openHEMSContext.schedule)) }

@view_config(
    route_name='states',
    renderer='json'
)
def states(request):
	states = {}
	for id, node in openHEMSContext.schedule.items():
		states[id] = node.toJson()
	return states

@view_config(
    route_name='schedule',
    renderer='json'
)
def schedule(request):
    return {"schedule": True}

class OpenhemsHTTPServer():
	def print_context(self):
		print("context", openHEMSContext)

	def __init__(self, schedule):
		global openHEMSContext
		self.schedule = schedule
		openHEMSContext = self

	def run(self):
		with Configurator() as config:
		    config.include('pyramid_jinja2')
		    config.add_route('panel', '/')
		    config.add_route('states', '/states')
		    config.add_route('schedule', '/schedule')
		    config.scan()
		    app = config.make_wsgi_app()
		server = make_server('0.0.0.0', 8000, app)
		server.serve_forever()


"""
from http import server
# SimpleHTTPRequestHandler


class OpenhemsHTTPRequestHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = "<html><p>hello world</p></html>"
        self.wfile.write(html.encode())

def OpenhemsHTTPServer():
    server_address = ('', 8000)
    httpd = server.HTTPServer(server_address, OpenhemsHTTPRequestHandler)
    httpd.serve_forever()

OpenhemsHTTPServer()
"""
