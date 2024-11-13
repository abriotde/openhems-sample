#!/usr/bin/env python3
"""
HTTP web server to give UI to configure OpenHEMS server:
* Set devices to schedule
* Switch on/offf VPN
* 
"""
import subprocess
import time
import json
from json import JSONEncoder
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
# from pyramid.response import Response
from pyramid.view import view_config
# from .schedule import OpenHEMSSchedule

# pylint: disable=unused-argument

# Patch for jsonEncoder
def wrappedDefault(self, obj):
	"""
	Patch for jsonEncoder
	"""
	return getattr(obj.__class__, "__json__", wrappedDefault.default)(obj)
wrappedDefault.default = JSONEncoder().default
# apply the patch
JSONEncoder.original_default = JSONEncoder.default
JSONEncoder.default = wrappedDefault

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

def testVPN():
	"""
	Use 'ip a| grep "wg0:"' to test if Wireguard VPN is Up.
	We could use "wg show" but it need to be root
	@return: bool : True if VPN is up, false else
	"""
	with subprocess.Popen( "ip a| grep 'wg0:'", \
				shell=True, stdout=subprocess.PIPE\
			) as fd:
		vpnInterfaces = fd.stdout.read()
		vpnInterfaces = str(vpnInterfaces).strip()
		nbInterfaces = len(vpnInterfaces)
		ok = nbInterfaces>3
		OPENHEMS_CONTEXT.logger.info("VPN is %s", 'up' if ok else 'down')
		return ok
	return False

def startVPN(start:bool=True):
	"""
	@param start: bool: if False stop the Wireguard's VPN else start it.
	"""
	cmd = "wg-quick "+("up" if start else "down")+" wg0"
	# Start the VPN
	with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE) as _:
		pass

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
			OPENHEMS_CONTEXT.schedule[i].setSchedule(node["duration"], node["timeout"])
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

	def __init__(self, mylogger, schedule, port=8000):
		self.logger = mylogger
		self.schedule = schedule
		self.port = port
		# pylint: disable=global-statement
		global OPENHEMS_CONTEXT
		OPENHEMS_CONTEXT = self
		testVPN()

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
			config.add_static_view(name='img', path='openhems.modules.web:../../../../img')
			config.scan()
			app = config.make_wsgi_app()
		server = make_server('0.0.0.0', self.port, app)
		server.serve_forever()
