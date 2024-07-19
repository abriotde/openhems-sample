#!/usr/bin/env python3
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
import json
from json import JSONEncoder
def wrapped_default(self, obj):
    return getattr(obj.__class__, "__json__", wrapped_default.default)(obj)
wrapped_default.default = JSONEncoder().default
# apply the patch
JSONEncoder.original_default = JSONEncoder.default
JSONEncoder.default = wrapped_default

from schedule import OpenHEMSSchedule

openHEMSContext = None

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
	print("GET:", vars(request.POST))
	# datas = json.loads(request.POST["_items"][0]);
	for id, node in request.POST.items():
		datas = json.loads(id)
	for id, node in datas.items():
		if id in openHEMSContext.schedule:
			openHEMSContext.schedule[id] = OpenHEMSSchedule(id, node["name"], node["duration"], node["timeout"])
		print("node:", id, node)
	# print("nodes:", datas)
	# for id, node in openHEMSContext.schedule.items():
	# 	states[id] = json.dumps(node)
	return openHEMSContext.schedule

@view_config(
    route_name='schedule',
    renderer='json'
)
def schedule(request):
    return {"schedule": True}

# @view_config(name='favicon.ico', route_name='../img/favicon.ico')
# def favicon_view(request):
#     return _fi_response

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
