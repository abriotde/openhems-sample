#!/usr/bin/env python3
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
import logging
import json
from json import JSONEncoder
# Patch for jsonEncoder
def wrapped_default(self, obj):
    return getattr(obj.__class__, "__json__", wrapped_default.default)(obj)
wrapped_default.default = JSONEncoder().default
# apply the patch
JSONEncoder.original_default = JSONEncoder.default
JSONEncoder.default = wrapped_default

from schedule import OpenHEMSSchedule

openHEMSContext = None
logger = logging.getLogger(__name__)

@view_config(
    route_name='panel',
    renderer='templates/panel.jinja2'
)
def panel(request):
    return { "nodes": openHEMSContext.schedule }

@view_config(
    route_name='states',
    renderer='json'
)
def states(request):
	for id, node in request.POST.items():
		datas = json.loads(id)
	# print("datas:", datas)
	for id, node in datas.items():
		if id in openHEMSContext.schedule:
			openHEMSContext.schedule[id].setSchedule(node["duration"], node["timeout"])
		else:
			logger.error("Node id='"+id+"' not found.")
	return openHEMSContext.schedule

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
		    # config.add_route('favicon.ico', '/favicon.ico')
		    config.add_static_view(name='img', path='web:../img')
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
