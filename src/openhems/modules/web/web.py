#!/usr/bin/env python3
"""
HTTP web server to give UI to configure OpenHEMS server:
* Set devices to schedule
* Switch on/offf VPN
* 
"""
import time
import json
from pathlib import Path
from json import JSONEncoder
import re
from wsgiref.simple_server import make_server
import yaml
from pyramid.config import Configurator
from pyramid.httpexceptions import exception_response
# from pyramid.response import Response
from pyramid.view import view_config
from openhems.modules.util import (
	ConfigurationManager, ConfigurationException, CastUtililty, CastException
)
from .driver_vpn import VpnDriverWireguard, VpnDriverIncronClient
# from .schedule import OpenHEMSSchedule

# Patch for jsonEncoder
# pylint: disable=unused-argument
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

ROOT_PATH = Path(__file__).parents[4]

@view_config(
	route_name='panel',
	renderer='templates/panel.jinja2'
)
def panel(request):
	"""
	Web-service to get schedled devices.
	"""
	del request
	return { "nodes": OPENHEMS_CONTEXT.schedule }

# pylint: disable=too-many-branches
def getNode(node, model):
	"""
	Implement on server side configuration checker.
	Something like populateNode() on params.js
	"""
	OPENHEMS_CONTEXT.logger.info(f"getNode({node}, {model})")
	newNode = None
	if isinstance(model, dict):
		if not isinstance(node, dict):
			raise ConfigurationException(f"Expecting a dict {node}")
		newNode = {}
		className = node.get("class")
		if className is not None: # Check the className exists as key in the model (We have a choice)
			model = model.get(className.lower())
			if model is None:
				raise ConfigurationException(f"Unexpected class '{className}'")
			newNode["class"] = className
		for k,smodel in model.items(): # Check we have all the field of the model
			snode = node.get(k)
			if snode is None:
				raise ConfigurationException(f"No field '{k}' in {node}")
			newNode[k] = getNode(snode, smodel)
	elif isinstance(model, list):
		if not isinstance(node, list):
			try:
				node = CastUtililty.toTypeList(node)
			except CastException as e:
				raise ConfigurationException(f"Expecting a list {node}") from e
		if len(model)>0:
			newNode = []
			smodel = model[0]
			for snode in node:
				newNode.append(getNode(snode, smodel))
		else:
			newNode = node
	else: # None, Str, Int... (!!! Maybe is it a Home-Assistant ident)
		newNode = node
	return newNode

def updateConfigurator(fields):
	"""
	Update configurator with form fields	
	"""
	configurator = ConfigurationManager(OPENHEMS_CONTEXT.logger)
	configurator.addYamlConfig(Path(OPENHEMS_CONTEXT.yamlConfFilepath))
	change = False
	for key, newValue in fields.items():
		currentValue = configurator.get(key)
		if isinstance(currentValue, list) and isinstance(newValue, str) \
				 and key == "network.nodes":
			val = configurator.get("default.node", deepSearch=True)
			model = [ConfigurationManager.toTree(val)]
			newValue = getNode(newValue, model)
		else:
			currentValue = str(currentValue)
		if currentValue!=newValue:
			print(currentValue, type(currentValue), " != ", newValue, type(newValue), " for key = ", key)
			configurator.add(key, newValue)
			change = True
	return change, configurator

@view_config(
	route_name='params',
	renderer='templates/params.jinja2'
)
def params(request):
	"""
	Web-page get all configurables params for params page and there value.
	"""
	try:
		change, configurator = updateConfigurator(request.params)
		if change:
			configurator.save(OPENHEMS_CONTEXT.yamlConfFilepath)
	except ConfigurationException as e:
		# NB : The real value can be None...
		OPENHEMS_CONTEXT.logger.warning(
			"/params : Unexpected error parsing parameters : %s",
			e.message
		)
		raise exception_response(400) from e # HTTPBadRequest

	# Display current configuration. Redo all for safety
	configurator = ConfigurationManager(OPENHEMS_CONTEXT.logger)
	configurator.addYamlConfig(Path(OPENHEMS_CONTEXT.yamlConfFilepath))
	params0 = configurator.get("", deepSearch=True)
	params1 = {}
	for k,v  in params0.items():
		params1[k.replace(".","_")] = v
	params1["vpn"] = "up" if OPENHEMS_CONTEXT.vpnDriver.testVPN() else "down"
	params1["availableNodes"] = configurator.getRawYamlConfig()['default']['node']
	params1["warningMessages"] = OPENHEMS_CONTEXT.warningMessages
	return params1

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
			OPENHEMS_CONTEXT.logger.info("Schedule(%s)", node)
			# Security: check inputs
			duration = CastUtililty.toTypeInt(node.get("duration"))
			try:
				timeout = node.get("timeout")
				if isinstance(timeout, int) and timeout==0:
					timeout = None
				else:
					timeout = CastUtililty.toTypeDatetime(timeout)
			except CastException as e:
				timeout = None
				OPENHEMS_CONTEXT.logger.warning("Fail cast to datetime %s : %s : Ignore timeout.", timeout,e)
			OPENHEMS_CONTEXT.schedule[i].setSchedule(duration, timeout)
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

	def __init__(self, mylogger, schedule, warningMessages, *,
			port=8000, htmlRoot="/", inDocker=False, configurator=None):
		self.logger = mylogger
		self.schedule = schedule
		self.warningMessages = warningMessages
		self.port = port
		self.htmlRoot = htmlRoot
		if configurator is None:
			configurator = ConfigurationManager(self.logger)
		if isinstance(configurator, str):
			self.yamlConfFilepath = configurator
			configurator = ConfigurationManager(self.logger)
			configurator.addYamlConfig(Path(self.yamlConfFilepath))
		else:
			self.yamlConfFilepath = configurator.getLastYamlConfFilepath()
		self.configurator = configurator
		lang = configurator.get("localization.language")
		self.translations = {}
		translationsPath = ROOT_PATH / ("data/keys_"+lang+".yaml")
		with translationsPath.open("r", encoding="utf-8") as keyFile:
			self.translations = yaml.load(keyFile, Loader=yaml.FullLoader)
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

	def getTemplateYamlParamsBodyHeaders(self, lastElems, elems):
		"""
		represent YAML (tooltip) as HTML Form.
		return: HTML code.
		"""
		htmlTabsMenu = ""
		htmlTabsBody = ""
		base = elems[:-1]
		oldBase = lastElems[:-1]
		if base!=oldBase:
			for i,e in enumerate(oldBase):
				if i>=len(base) or base[i]!=e:
					htmlTabsBody += "</div>\n"
			if len(lastElems)==0 or lastElems[0]!=elems[0]:
				tabName = elems[0]
				htmlTabsMenu+='<li><a href="#tabs-'+tabName+'">' \
					+ tabName.capitalize() + '</a></li>\n'
				htmlTabsBody+='<div id="tabs-'+tabName+'">\n'
				paragraph = self.translations["htmlTitleDescriptions"].get(tabName)
				if paragraph is not None:
					htmlTabsBody += (f"<p>{paragraph}</p>\n")
			for i,e in enumerate(base[1:]):
				j = i+1
				if j>=len(oldBase) or lastElems[j]!=e:
					headerLevel = j+1
					header = e.capitalize()
					htmlTabsBody += (f"<div class='config_{i}'>\n"
						f"<h{headerLevel}>{header}</h{headerLevel}>\n")
		return (htmlTabsMenu, htmlTabsBody)

	def getTemplateYamlParamsBody(self, tooltips:dict):
		"""
		represent YAML (tooltip) as HTML Form.
		return: HTML code.
		"""
		htmlTabsMenu = ""
		htmlTabsBody = ""
		lastElems = []
		for name, tooltip in tooltips.items():
			elems = name.split(".")
			grade = len(elems)-1
			m, b = self.getTemplateYamlParamsBodyHeaders(lastElems, elems)
			htmlTabsMenu += m
			htmlTabsBody += b
			jinja2Id = name.replace('.','_')
			label = re.sub(r'(?<!^)(?=[A-Z])', ' ',elems[grade]).capitalize()
			if name=="network.nodes":
				tagAttributes = 'type="hidden"'
				htmlTabsElem += ('<button type="button" '
					' onclick="displayAddNodePopup()">+</button>')
			else:
				htmlTabsElem = ''
				tagAttributes = 'type="text"'
			htmlTabsBody += ('<div class="row"><div class="col-25">'
				f'<label for="{name}">{label}:</label>'
				'</div><div class="col-75">' + htmlTabsElem +
				'<input '+tagAttributes+f' id="{name}" '
					f'name="{name}" title="{tooltip}"'
					' value="{{ '+jinja2Id+' }}" />'
					'</div></div><br>\n')
			if name=="network.nodes":
				htmlTabsBody += '<div id="nodes"></div>\n'
			lastElems = elems
		htmlTabsBody += ("</div>\n"*(len(lastElems)-1))
		return "<ul>"+htmlTabsMenu+"</ul>"+htmlTabsBody

	def generateTemplateYamlParams(self, lang="en"):
		"""
		Generate the template file for /params page based on YAML configuration file.
		"""
		templatesPath = Path(__file__).parents[0]/"templates"
		tooltipPath = ROOT_PATH / ("data/openhems_tooltips_"+lang+".yaml")
		configurator = ConfigurationManager(self.logger, defaultPath=tooltipPath)
		tooltips = configurator.get("", deepSearch=True)
		frameworkPath = templatesPath / "params.framework.jinja2"
		with frameworkPath.open("r", encoding="utf-8") as infile:
			datas = infile.read()
		htmlHead, htmlQueue = datas.split("{%YAML_PARAMS%}")
		yamlparamsPath = templatesPath / "params.jinja2"
		with yamlparamsPath.open("w", encoding="utf-8") as outfile:
			outfile.write(htmlHead)
			outfile.write(self.getTemplateYamlParamsBody(tooltips))
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
