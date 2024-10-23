#!/usr/bin/env python3
"""
HTTP web server to give UI to configure OpenHEMS server:
* Set devices to schedule
* Switch on/offf VPN
* 
"""
import logging
import subprocess
import time
import json
from json import JSONEncoder
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
# from pyramid.response import Response
from pyramid.view import view_config
# from .schedule import OpenHEMSSchedule

# Patch for jsonEncoder
# pylint: disable=unused-argument
def wrapped_default(self, obj):
	"""
	Patch for jsonEncoder
	"""
	return getattr(obj.__class__, "__json__", wrapped_default.default)(obj)
wrapped_default.default = JSONEncoder().default
# apply the patch
JSONEncoder.original_default = JSONEncoder.default
JSONEncoder.default = wrapped_default

openHEMSContext = None
logger = logging.getLogger(__name__)

@view_config(
    route_name='panel',
    renderer='templates/panel.jinja2'
)
# pylint: disable=unused-argument
def panel(request):
	"""
	Web-service to get schedled devices.
	"""
	return { "nodes": openHEMSContext.schedule }

def testVPN():
	"""
	Use 'ip a| grep "wg0:"' to test if Wireguard VPN is Up.
	We could use "wg show" but it need to be root
	@return: bool : True if VPN is up, false else
	"""
	with subprocess.Popen(\
		"ip a| grep 'wg0:'", \
		shell=True, stdout=subprocess.PIPE\
	).stdout.read() as vpn_interfaces:
		vpn_interfaces = str(vpn_interfaces).strip()
		nb_interfaces = len(vpn_interfaces)
		logger.info("VPN is "+("up" if (nb_interfaces>3) else "down"))
		return nb_interfaces>3
	return False

def startVPN(start:bool=True):
	"""
	@param start: bool: if False stop the Wireguard's VPN else start it.
	"""
	cmd = "wg-quick "+("up" if start else "down")+" wg0"
	# Start the VPN
	subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

@view_config(
	route_name='params',
	renderer='templates/params.jinja2'
)
def params(request):
	"""
	Get all configurables params for params page and there value.
	"""
	return { "vpn": "up" if testVPN() else "down" }

@view_config(
    route_name='vpn',
    renderer='json'
)
# pylint: disable=unused-argument
def vpn(request):
	"""
	Web-service to connect/disconnect the VPN
	"""
	print("request.GET", request.GET)
	connect = request.GET.get("connect")=="true"
	if connect:
		startVPN()
	else:
		startVPN(False)
	time.sleep(3)
	connected = testVPN()
	logger.info("/vpn?{}connect : {}"\
		.format(("" if connect else "dis"), str(connected==connect)))
	return { "connected": connected }

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
			logger.error("Node id='%s' not found."%id)
	return openHEMSContext.schedule

class OpenhemsHTTPServer():
	def print_context(self):
		"""
		For debug
		"""
		print("context", openHEMSContext)

	def __init__(self, schedule):
		testVPN()
		global openHEMSContext
		self.schedule = schedule
		openHEMSContext = self

	def run(self):
		"""
		Launch the web server.
		"""
		with Configurator() as config:
			config.include('pyramid_jinja2')
			config.add_route('panel', '/')
			config.add_route('states', '/states')
			config.add_route('params', '/params')
			config.add_route('vpn', '/vpn')
			# config.add_route('favicon.ico', '/favicon.ico')
			config.add_static_view(name='img', path='modules.web:../../../img')
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
