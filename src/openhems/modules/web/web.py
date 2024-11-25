#!/usr/bin/env python3
"""
HTTP web server to give UI to configure OpenHEMS server:
* Set devices to schedule
* Switch on/offf VPN
* 
"""
import time
import json
from json import JSONEncoder
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
# from pyramid.response import Response
from pyramid.view import view_config
from .driver_vpn import VpnDriverWireguard, VpnDriverIncronClient
# from .schedule import OpenHEMSSchedule

OPENHEMS_CONTEXT = None

@view_config(
    route_name='panel',
    renderer='templates/panel.jinja2'
)
def panel(request):
	"""
	Web-service to get schedled devices.
	"""
	return { "nodes": OPENHEMS_CONTEXT.schedule }

@view_config(
	route_name='params',
	renderer='templates/params.jinja2'
)
def params(request):
	"""
	Get all configurables params for params page and there value.
	"""
	return { "vpn": "up" if OPENHEMS_CONTEXT.vpnDriver.testVPN() else "down" }

@view_config(
    route_name='vpn',
    renderer='json'
)
def vpn(request):
	"""
	Web-service to connect/disconnect the VPN
	"""
	print("request.GET", request.GET)
	connect = request.GET.get("connect")=="true"
	if connect:
		OPENHEMS_CONTEXT.vpnDriver.startVPN()
	else:
		OPENHEMS_CONTEXT.vpnDriver.startVPN(False)
	time.sleep(3)
	connected = OPENHEMS_CONTEXT.vpnDriver.testVPN()
	OPENHEMS_CONTEXT.logger.info("/vpn?%sconnect : {%s}",
		'' if connect else 'dis', 
		connected==connect)
	return { "connected": connected }

@view_config(
    route_name='states',
    renderer='json'
)
def states(request):
	"""
	Web service to get scheduledd devices.
	"""
	for i, node in request.POST.items():
		datas = json.loads(i)
	# print("datas:", datas)
	for i, node in datas.items():
		if i in OPENHEMS_CONTEXT.schedule:
			OPENHEMS_CONTEXT.schedule[i].setSchedule(
				duration=node["duration"],
				energy=node["energy"],
				timeout=node["timeout"]
			)
		else:
			OPENHEMS_CONTEXT.logger.error("Node id='%s' not found.",i)
	return OPENHEMS_CONTEXT.schedule

class OpenhemsHTTPServer():
	"""
	Class for HTTP Server for OpenHEMS UI configuration
	"""
	def printContext(self):
		"""
		For debug
		"""
		print("context", OPENHEMS_CONTEXT)

	def __init__(self, mylogger, schedule, port=8000, htmlRoot="/", inDocker=False):
		self.logger = mylogger
		self.schedule = schedule
		self.port = port
		self.htmlRoot = htmlRoot
		if inDocker:
			vpnDriver = VpnDriverIncronClient(mylogger)
		else:
			vpnDriver = VpnDriverWireguard(mylogger)
		self.vpnDriver = vpnDriver
		# pylint: disable=global-statement
		global OPENHEMS_CONTEXT
		OPENHEMS_CONTEXT = self
		OPENHEMS_CONTEXT.vpnDriver.testVPN()

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
			root = (self.htmlRoot+'/img').replace('//','/')
			print("ROOT:",root)
			config.add_static_view(
				name=root,
				path='openhems.modules.web:../../../../img'
			)
			config.scan()
			app = config.make_wsgi_app()
		host = '0.0.0.0'
		server = make_server(host, self.port, app)
		self.logger.info("HTTP server is listening on '%s:%d'", host, self.port)
		server.serve_forever()
