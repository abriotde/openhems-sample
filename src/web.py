#!/usr/bin/env python3

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config

@view_config(
    route_name='panel',
    renderer='templates/panel.jinja2'
)
def panel(request):
    return {"greet": 'Welcome', "name": 'Akhenaten'}

@view_config(
    route_name='states',
    renderer='json'
)
def states(request):
    return {"states": 1, "b": 2}

@view_config(
    route_name='schedule',
    renderer='json'
)
def schedule(request):
    return {"schedule": 1, "b": 2}

class OpenhemsHTTPServer():
	def __init__(self):
		pass
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
