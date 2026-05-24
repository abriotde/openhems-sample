#!/usr/bin/env python3
"""
HTTP web server to give UI to configure OpenHEMS server:
* Set devices to schedule
* Switch on/offf VPN
*
"""
# pylint: skip-file
import time
import json
from pathlib import Path
from json import JSONEncoder
import re
import copy
from wsgiref.simple_server import make_server
import yaml
from pyramid.config import Configurator
from pyramid.httpexceptions import exception_response
# from pyramid.response import Response
from pyramid.view import view_config
from openhems.modules.util import (
    ConfigurationManager, ConfigurationException, CastUtililty, CastException, ProjectConfiguration
)
from .driver_vpn import VpnDriverWireguard, VpnDriverIncronClient
# from openhems.schedule import OpenHEMSSchedule

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

OPENHEMS_CONTEXT = None

ROOT_PATH = Path(__file__).parents[2]

@view_config(
    route_name='panel',
    renderer='templates/panel.jinja2'
)
def panel(request):
    """
    Web-service to get schedled devices.
    """
    del request
    panel_params = OPENHEMS_CONTEXT.translations["web"]
    panel_params["nodes"] = OPENHEMS_CONTEXT.schedule
    return panel_params

# pylint: disable=too-many-branches
def get_node(node, model):
    """
    Implement on server side configuration checker.
    Check that it don't set unknown parameters (for security)
    Something like populateNode() on params.js
    """
    OPENHEMS_CONTEXT.logger.debug(f"get_node({node}, {model})")
    new_node = None
    if isinstance(model, dict):
        if not isinstance(node, dict):
            raise ConfigurationException(f"Expecting a dict {node} for model {model}")
        new_node = {}
        class_name = node.get("class")
        myid = node.get("id")
        if class_name is not None:
            # Check the class_name exists as key in the model (We have a choice)
            model = model.get(class_name.lower())
            if model is None:
                raise ConfigurationException(f"Unexpected class '{class_name}'")
            new_node["class"] = class_name
        for k, smodel in model.items(): # Check we have all the field of the model
            snode = node.get(k)
            if snode is None:
                raise ConfigurationException(f"No field '{k}' in {node}")
            new_node[k] = get_node(snode, smodel)
        new_node["id"] = myid
    elif isinstance(model, list):
        if not isinstance(node, list):
            try:
                node = CastUtililty.toTypeList(node)
            except CastException as e:
                raise ConfigurationException(f"Expecting a list {node}") from e
        if len(model) > 0:
            new_node = []
            smodel = model[0]
            for snode in node:
                new_node.append(get_node(snode, smodel))
        else:
            new_node = node
    else: # None, Str, Int... (!!! Maybe is it a Home-Assistant ident)
        new_node = node
    return new_node

def update_configurator(fields):
    """
    Update configurator with form fields
    """
    if len(fields) == 0: # When no update is needed (Call /params)
        # We get back configurator as it was loaded
        # for case we loaded many files (openhems.yaml & openhems.secret.yaml)
        configurator = OPENHEMS_CONTEXT.configurator
    else: # Call /params with update parameters
        # We get configurator as it ougth to be on last file (openhems.secret.yaml)
        configurator = ConfigurationManager(OPENHEMS_CONTEXT.logger)
        configurator.addYamlConfig(Path(OPENHEMS_CONTEXT.yaml_conf_filepath))
    configurator.completeWithDefaults()

    change = False
    for key, new_value in fields.items():
        OPENHEMS_CONTEXT.logger.debug("update_configurator() GET %s : %s", key, new_value)
        current_value = configurator.get(key)
        hook = ConfigurationManager.HOOKS.get(key)
        if hook is not None:
            val = configurator.get("default." + hook, deepSearch=True)
            model = ConfigurationManager.toTree(val)
            model = [model]
            new_value = CastUtililty.toTypeList(new_value)
            new_value = get_node(new_value, model)
            OPENHEMS_CONTEXT.logger.debug("update_configurator() : Update %s : %s \n -> %s",
                                          key, current_value, new_value)
        else:
            current_value = str(current_value)
        if current_value != new_value:
            # print(current_value, type(current_value), " != ", new_value,
			#   type(new_value), " for key = ", key)
            try:
                configurator.add(key, new_value)
            except ConfigurationException as e:
                # NB : The real value can be None...
                OPENHEMS_CONTEXT.logger.warning(
                    "/params : Unexpected parameter : %s!=%s for key=%s : %s",
                    current_value, new_value, key, e.message
                )
            change = True
    if change: # We update configurator
        OPENHEMS_CONTEXT.configurator = configurator
    return change, configurator

@view_config(
    route_name='about',
    renderer='templates/about.jinja2'
)
def about(request):
    """
    Web-page get all general informations.
    """
    conf = ProjectConfiguration()
    vals = {
        "name": conf.getName(),
        "version": conf.getVersion(),
        "licence": conf.getLicence(),
        "urls": conf.getUrls(),
    }
    return vals


@view_config(
    route_name='params',
    renderer='templates/params.jinja2'
)
def params(request):
    """
    Web-page get all configurables params for params page and there value.
    """
    try:
        change, configurator = update_configurator(request.params)
        if change:
            configurator.save(OPENHEMS_CONTEXT.yaml_conf_filepath)
            # Display current configuration. Redo all for safety
            configurator = ConfigurationManager(OPENHEMS_CONTEXT.logger)
            configurator.addYamlConfig(Path(OPENHEMS_CONTEXT.yaml_conf_filepath))
    except ConfigurationException as e:
        # NB : The real value can be None...
        OPENHEMS_CONTEXT.logger.warning(
            "/params : Unexpected error parsing parameters : %s",
            e.message
        )
        raise exception_response(400) from e # HTTPBadRequest

    params0 = configurator.get("", deepSearch=True)
    params1 = {}
    for k, v in params0.items():
        params1[k.replace(".", "_")] = v
    params1["vpn"] = "up" if OPENHEMS_CONTEXT.vpn_driver.test_vpn() else "down"
    params1["available_nodes"] = {}
    node_types = ['node', 'strategy']
    raw_config = configurator.getRawYamlConfig()
    for node_type in node_types:
        params1["available_nodes"][node_type] = raw_config['default'][node_type]
    params1["warning_messages"] = OPENHEMS_CONTEXT.warning_messages
    OPENHEMS_CONTEXT.logger.debug("generate /params with %s", params1)
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
    connect = request.GET.get("connect") == "true"
    if connect:
        OPENHEMS_CONTEXT.vpn_driver.start_vpn()
    else:
        OPENHEMS_CONTEXT.vpn_driver.start_vpn(False)
    time.sleep(3)
    connected = OPENHEMS_CONTEXT.vpn_driver.test_vpn()
    OPENHEMS_CONTEXT.logger.info("/vpn?%sconnect : {%s}",
                                 '' if connect else 'dis',
                                 connected == connect)
    return {"connected": connected}

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
                if isinstance(timeout, int) and timeout == 0:
                    timeout = None
                else:
                    timeout = CastUtililty.toTypeDatetime(timeout)
            except CastException as e:
                timeout = None
                OPENHEMS_CONTEXT.logger.warning(
                    "Fail cast to datetime %s : %s : Ignore timeout.",
                    timeout, e
                )
            OPENHEMS_CONTEXT.schedule[i].set_schedule(duration, timeout)
        else:
            OPENHEMS_CONTEXT.logger.error("Node id='%s' not found.", i)
    return OPENHEMS_CONTEXT.schedule

class OpenhemsHTTPServer():
    """
    Class for HTTP Server for OpenHEMS UI configuration
    """
    def print_context(self):
        """
        For debug
        """
        print("context", OPENHEMS_CONTEXT)

    def __init__(self, mylogger, schedule, warning_messages, *,
                 port=8000, html_root="/", in_docker=False, configurator=None):
        self.logger = mylogger
        self.schedule = schedule
        self.warning_messages = warning_messages
        self.port = port
        self.html_root = html_root
        if configurator is None:
            configurator = ConfigurationManager(self.logger)
        if isinstance(configurator, str):
            self.yaml_conf_filepath = configurator
            configurator.defaultPath = ConfigurationManager.DEFAULT_PATH
            configurator = ConfigurationManager(self.logger)
            configurator.addYamlConfig(Path(self.yaml_conf_filepath))
        else:
            self.yaml_conf_filepath = configurator.getLastYamlConfFilepath()
        self.default_conf_filepath = configurator.defaultPath
        self.configurator = configurator
        lang = configurator.get("localization.language")
        self.translations = {}
        translations_path = ROOT_PATH / ("data/keys_" + lang + ".yaml")
        with translations_path.open("r", encoding="utf-8") as key_file:
            self.translations = yaml.load(key_file, Loader=yaml.FullLoader)
        if in_docker:
            vpn_driver = VpnDriverIncronClient(mylogger)
        else:
            vpn_driver = VpnDriverWireguard(mylogger)
        self.vpn_driver = vpn_driver
        # pylint: disable=global-statement
        global OPENHEMS_CONTEXT
        OPENHEMS_CONTEXT = self
        OPENHEMS_CONTEXT.vpn_driver.test_vpn()
        self.generate_template_yaml_params(lang)

    def get_template_yaml_params_body_headers(self, last_elems, elems):
        """
        represent YAML (tooltip) as HTML Form.
        return: HTML code.
        """
        html_tabs_menu = ""
        html_tabs_body = ""
        base = elems[:-1]
        old_base = last_elems[:-1]
        if base != old_base:
            for i, e in enumerate(old_base):
                if i >= len(base) or base[i] != e:
                    html_tabs_body += "</div>\n"
            if len(last_elems) == 0 or last_elems[0] != elems[0]:
                tab_name = elems[0]
                html_tabs_menu += '<li><a href="#tabs-' + tab_name + '">' \
                                  + tab_name.capitalize() + '</a></li>\n'
                html_tabs_body += '<div id="tabs-' + tab_name + '">\n'
                paragraph = self.translations["htmlTitleDescriptions"].get(tab_name)
                if paragraph is not None:
                    html_tabs_body += (f"<p>{paragraph}</p>\n")
            for i, e in enumerate(base[1:]):
                j = i + 1
                if j >= len(old_base) or last_elems[j] != e:
                    header_level = j + 1
                    header = e.capitalize()
                    html_tabs_body += (f"<div class='config_{i}'>\n"
                                       f"<h{header_level}>{header}</h{header_level}>\n")
        return (html_tabs_menu, html_tabs_body)

    # pylint: disable=too-many-locals
    def get_template_yaml_params_body(self, tooltips: dict):
        """
        represent YAML (tooltip) as HTML Form.
        return: HTML code.
        """
        html_tabs_menu = ""
        html_tabs_body = ""
        last_elems = []
        for name, tooltip in tooltips.items():
            elems = name.split(".")
            grade = len(elems) - 1
            m, b = self.get_template_yaml_params_body_headers(last_elems, elems)
            html_tabs_menu += m
            html_tabs_body += b
            jinja2_id = name.replace('.', '_')
            label = re.sub(r'(?<!^)(?=[A-Z])', ' ', elems[grade]).capitalize()
            hook = ConfigurationManager.HOOKS.get(name)
            if hook is not None:  # strategy or network node
                tag_attributes = 'type="hidden"'
                html_tabs_elem = ('<button type="button" '
                                  ' onclick="displayAddNodePopup(\'' + hook + '\')">+</button>')
            else:
                tag_attributes = 'type="text"'
                html_tabs_elem = ''
            html_tabs_body += ('<div class="row"><div class="col-25">'
                               f'<label for="{name}">{label}:</label>'
                               '</div><div class="col-75">' + html_tabs_elem +
                               '<input ' + tag_attributes + f' id="{name}" '
                               f'name="{name}" title="{tooltip}"'
                               ' value="{{ ' + jinja2_id + ' }}">'
                                                                   '</div></div><br>\n')
            if hook is not None:  # strategy or network node.
                # 'strategys' is huggly, but it's simpler...
                html_tabs_body += '<div id="' + hook + 's"></div>\n'
                html_tabs_body += ('<script>' + hook + 's = {{ '
                                   + jinja2_id + '|tojson }};</script>\n')
            last_elems = elems
        html_tabs_body += ("</div>\n" * (len(last_elems) - 1))
        html_tabs = "<ul>" + html_tabs_menu + "</ul>" + html_tabs_body
        html_tabs += "\n<script>var tooltips = " + json.dumps(tooltips) + ";</script>"
        return html_tabs

    def get_tooltips(self, lang="en"):
        """
        Get tooltips from configuration in right language and add default values.
        """
        self.logger.debug("get_tooltips(%s)", lang)
        tooltip_path = ROOT_PATH / ("data/openhems_tooltips_" + lang + ".yaml")
        configurator = ConfigurationManager(self.logger, defaultPath=tooltip_path)
        tooltips = configurator.get("", deepSearch=True)
        default_config = ConfigurationManager(self.default_conf_filepath)
        tooltips2 = copy.deepcopy(tooltips)
        tooltip_with_default = self.translations["web"].get("defaultTooltip")
        for key, tooltip in tooltips.items():
            # self.logger.debug("Tooltip: %s : %s", key, tooltip)
            default_value = default_config.get(key)
            if default_value is not None and str(default_value) != "":
                local_vars = locals()
                local_vars["tooltip"] = tooltip  # else tooltip seam not used by Python checker.
                value = tooltip_with_default.format(**local_vars)
                # self.logger.debug("Tooltip with default: %s : %s", key, value)
                tooltips2[key] = value
        return tooltips2

    def generate_template_yaml_params(self, lang="en"):
        """
        Generate the template file for /params page based on YAML configuration file.
        """
        self.logger.debug("generate_template_yaml_params(%s)", lang)
        OPENHEMS_CONTEXT.logger.info("Generate template for /params page")
        tooltips = self.get_tooltips(lang)
        templates_path = Path(__file__).parents[0] / "templates"
        framework_path = templates_path / "params.framework.jinja2"
        with framework_path.open("r", encoding="utf-8") as infile:
            datas = infile.read()
        html_head, html_queue = datas.split("{%YAML_PARAMS%}")
        yamlparams_path = templates_path / "params.jinja2"
        with yamlparams_path.open("w", encoding="utf-8") as outfile:
            outfile.write(html_head)
            outfile.write(self.get_template_yaml_params_body(tooltips))
            outfile.write(html_queue)

    def run(self):
        """
        Launch the web server.
        """
        with Configurator() as config:
            config.include('pyramid_jinja2')
            config.add_route('panel', '/')
            config.add_route('states', '/states')
            config.add_route('params', '/params')
            config.add_route('about', '/about')
            config.add_route('vpn', '/vpn')
            # config.add_route('favicon.ico', '/favicon.ico')
            img_url = (self.html_root + '/img').replace('//', '/')
            js_url = (self.html_root + '/js').replace('//', '/')
            css_url = (self.html_root + '/css').replace('//', '/')
            favicon_url = (self.html_root + '/favicon.ico').replace('//', '/')
            config.add_static_view(
                name=img_url,
                path='openhems.modules.web:img'
            )
            config.add_static_view(
                name=js_url,
                path='openhems.modules.web:js'
            )
            config.add_static_view(
                name=css_url,
                path='openhems.modules.web:css'
            )
            config.add_static_view(
                name=favicon_url,
                path='openhems.modules.web:img/favicon.ico'
            )
            config.scan()
            app = config.make_wsgi_app()
        host = '0.0.0.0'
        server = make_server(host, self.port, app)
        self.logger.info("HTTP server is listening on '%s:%d'", host, self.port)
        server.serve_forever()
