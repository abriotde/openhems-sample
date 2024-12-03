#!/usr/bin/env python3
"""
HTTP web server to give UI to configure OpenHEMS server:
* Set devices to schedule
* Switch on/offf VPN
* 
"""
import time
import json
import yaml
import re
from pathlib import Path
from json import JSONEncoder
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.httpexceptions import exception_response
# from pyramid.response import Response
from pyramid.view import view_config
from .driver_vpn import VpnDriverWireguard, VpnDriverIncronClient
# from .schedule import OpenHEMSSchedule
from openhems.modules.util.configuration_manager import ConfigurationManager

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

@view_config(
	route_name='params',
	renderer='templates/params.jinja2'
)
def params(request):
	"""
	Web-page get all configurables params for params page and there value.
	"""
	return { "vpn": "up" if OPENHEMS_CONTEXT.vpnDriver.testVPN() else "down" }

@view_config(
	route_name='yamlparams',
	renderer='templates/yamlparams.jinja2'
)
def yamlparams(request):
	"""
	Web-page get all configurables params for params page and there value.
	"""
	configurator = ConfigurationManager(OPENHEMS_CONTEXT.logger)
	configurator.addYamlConfig(Path(OPENHEMS_CONTEXT.yamlConfFilepath))
	newValues = {}
	change = False
	for key, newValue in request.params.items():
		currentValue = configurator.get(key)
		if currentValue!=newValue:
			try:
				configurator.add(key, newValue)
				change = True
			except ConfigurationException as e:
				# NB : The real value can be None...
				OPENHEMS_CONTEXT.logger.warning(
					"/yamlparams : Unexpected key %s' with config '%s'",
					key, OPENHEMS_CONTEXT.yamlConfFilepath
				)
				raise exception_response(400) # HTTPBadRequest
	if change:
		configurator.save(OPENHEMS_CONTEXT.yamlConfFilepath)

	# Display current configuration. Redo all for safety
	configurator = ConfigurationManager(OPENHEMS_CONTEXT.logger)
	configurator.addYamlConfig(Path(OPENHEMS_CONTEXT.yamlConfFilepath))
	params0 = configurator.get("", deepSearch=True)
	params = {}
	for k,v  in params0.items():
		params[k.replace(".","_")] = v
	params["vpn"] = "up" if OPENHEMS_CONTEXT.vpnDriver.testVPN() else "down"
	return params

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
	Web service to get scheduled devices.
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

	def __init__(self, mylogger, schedule, yamlConfFilepath, *, 
			port=8000, htmlRoot="/", inDocker=False, configurator=None):
		self.logger = mylogger
		self.schedule = schedule
		self.port = port
		self.htmlRoot = htmlRoot
		self.yamlConfFilepath = yamlConfFilepath
		if configurator is None:
			configurator = ConfigurationManager(self.logger)
			configurator.addYamlConfig(Path(self.yamlConfFilepath))
		self.configurator = configurator
		lang = configurator.get("localization.language")
		self.generateTemplateYamlParams(lang)
		if inDocker:
			vpnDriver = VpnDriverIncronClient(mylogger)
		else:
			vpnDriver = VpnDriverWireguard(mylogger)
		self.vpnDriver = vpnDriver
		# pylint: disable=global-statement
		global OPENHEMS_CONTEXT
		OPENHEMS_CONTEXT = self
		OPENHEMS_CONTEXT.vpnDriver.testVPN()

	def generateTemplateYamlParams(self, lang="en"):
		rootPath = Path(__file__).parents[4]
		templatesPath = Path(__file__).parents[0]/"templates"
		tooltipPath = rootPath / ("data/openhems_tooltips_"+lang+".yaml")
		configurator = ConfigurationManager(self.logger, defaultPath=tooltipPath)
		keysPath = rootPath / ("data/keys_"+lang+".yaml")
		keys = {}
		with keysPath.open("r", encoding="utf-8") as keyFile:
			keys = yaml.load(keyFile, Loader=yaml.FullLoader)
			descriptions = keys["htmlTitleDescriptions"]
		
		tooltips = configurator.get("", deepSearch=True)
		oldBase = ""
		oldgrade = 0
		frameworkPath = templatesPath / "yamlparams.framework.jinja2"
		with frameworkPath.open("r", encoding="utf-8") as infile:
			datas = infile.read()
		htmlHead, htmlQueue = datas.split("{%YAML_PARAMS%}")

		yamlparamsPath = templatesPath / "yamlparams.jinja2"
		with yamlparamsPath.open("w", encoding="utf-8") as outfile:
			outfile.write(htmlHead)
			for name, tooltip in tooltips.items():
				elems = name.split(".")
				base = ".".join(elems[:-1])
				grade = len(elems)-1
				if base!=oldBase:
					for g in range(grade, oldgrade+1):
						outfile.write(f"</div>\n")
					for g in range(oldgrade if oldgrade>0 else 1, grade+1):
						headerLevel = g+2
						header = elems[g-1].capitalize()
						outfile.write(f"<div class='config_{g}'>\n"
							f"<h{headerLevel}>{header}</h{headerLevel}>\n")
						if g==0:
							paragraph = descriptions.get(header)
							if paragraph is not None:
								outfile.write(f"<p>{paragraph}</p>\n")
					oldBase = base
					oldgrade = grade
				jinja2Id = name.replace('.','_')
				label = re.sub(r'(?<!^)(?=[A-Z])', ' ',elems[grade]).capitalize()
				outfile.write(f'<label for="{name}">{label}:</label>'
					f'<input type="text" id="{name}" name="{name}" title="{tooltip}"'
					' value="{{ '+jinja2Id+' }}" /><br>\n')
			for g in range(0, oldgrade+1):
				outfile.write(f"</div>\n")
			outfile.write(htmlQueue)
		

	def run(self):
		"""
		Launch the web server.
		"""
		with Configurator() as config:
			config.include('pyramid_jinja2')
			config.add_route('panel', '/')
			config.add_route('states', '/states')
			config.add_route('params', '/params')
			config.add_route('yamlparams', '/yamlparams')
			config.add_route('vpn', '/vpn')
			# config.add_route('favicon.ico', '/favicon.ico')
			root = (self.htmlRoot+'/img').replace('//','/')
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
