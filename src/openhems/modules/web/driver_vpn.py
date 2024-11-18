"""
Thos module is used to monitor/drive VPN.
"""
import subprocess
import time
from pathlib import Path

class VpnDriverWireguard:
	"""
	Start/stop/test a VPN Wireguard
	"""
	def __init__(self, logger, vpnInterface="wgo"):
		self.vpnInterface = vpnInterface
		self.logger = logger

	def testVPN(self):
		"""
		Use 'ip a| grep "wg0:"' to test if Wireguard VPN is Up.
		We could use "wg show" but it need to be root
		@return: bool : True if VPN is up, false else
		"""
		with subprocess.Popen( "ip a| grep '"+self.vpnInterface+":'", \
					shell=True, stdout=subprocess.PIPE\
				) as fd:
			vpnInterfaces = fd.stdout.read()
			vpnInterfaces = str(vpnInterfaces).strip()
			nbInterfaces = len(vpnInterfaces)
			ok = nbInterfaces>3
			self.logger.info("VPN is %s", 'up' if ok else 'down')
			return ok
		return False

	def startVPN(self, start:bool=True):
		"""
		@param start: bool: if False stop the Wireguard's VPN else start it.
		"""
		cmd = "wg-quick "+("up" if start else "down")+" "+self.vpnInterface
		# Start the VPN
		with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE) as _:
			pass

class VpnDriverIncronServer:
	"""
	It's not a daemond, it use incrontab daemond to serve client.

	!!! WARNING !!!
	 It is not thread safe, but as there should have only one client,
	 and not so much request, it's enough and simple.
	"""
	def __init__(self, logger, pathVpn="/data/vpn"):
		self.logger = logger
		self.pathVpn = Path(pathVpn)
		self.requestFile = self.pathVpn / 'request'
		self.responseFile = self.pathVpn / 'response'
		self.driver = VpnDriverWireguard(logger)

	def response(self, up=None):
		"""
		Write VPN status on self.responseFile.
		"""
		if up is None:
			up = self.driver.testVPN()
		msg = "up" if up else "down"
		with self.responseFile.open("w", encoding='utf-8') as f:
			f.write(msg)
			self.logger.info("VPN Status = %s", msg)
			return up
		return ''

	def startVPN(self):
		"""
		Start the VPN using 'driver'
		"""
		self.logger.info("Start VPN")
		self.driver.startVPN()
		self.testVPN()
	def stopVPN(self):
		"""
		Stop the VPN using 'driver'
		"""
		self.logger.info("Stop VPN")
		self.driver.startVPN(False)
		self.testVPN()
	def testVPN(self):
		"""
		Test the VPN using 'driver'
		"""
		up = self.driver.testVPN()
		response = self.response(up)
		self.logger.info("VPN Status = '%s'", response)
		return up

	def run(self):
		"""
		The function is called, each time self.requestFile is accessed.
		"""
		with self.requestFile.open("r", encoding='utf-8') as f:
			action = f.read().strip()
			if action == "start":
				self.startVPN()
			elif action == "stop":
				self.stopVPN()
			elif action == "test":
				self.testVPN()
			else:
				self.logger.error("Uknwon VPN action : '%s'", action)

	def runServer(self):
		"""
		Run a real server witch check the request file...
		 It is not the goal but used when there is no incron
		  (Debian Buleseye).
		 It should be better to use FIFO... 
		 but  won't be compatible with incron.
		"""
		up = self.driver.testVPN()
		lastAction = "start" if up else "stop"
		while True:
			with self.requestFile.open("r", encoding='utf-8') as f:
				action = f.read().strip()
				if lastAction!=action:
					if action == "start":
						self.startVPN()
					elif action == "stop":
						self.stopVPN()
					elif action == "test":
						up = self.testVPN()
					else:
						self.logger.error("Uknwon VPN action : '%s'", action)
					lastAction = action
			time.sleep(10)

class VpnDriverIncronClient:
	"""
	Used in docker container to start/stop/test host VPN
	Use shared repository beetwen Docker and Host /data:/opt.
	"""
	def __init__(self, logger, pathVpn="/opt/vpn"):
		self.logger = logger
		self.pathVpn = Path(pathVpn)
		self.requestFile = self.pathVpn / 'request'
		self.responseFile = self.pathVpn / 'response'

	def startVPN(self, start:bool=True):
		"""
		Use /opt/vpn/request file to send request to Host (or priviledged user).
		@param start: bool: if False stop the Wireguard's VPN else start it.
		"""
		request = "start" if start else "stop"
		with self.requestFile.open("w", encoding='utf-8') as f:
			f.write(request)

	def testVPN(self):
		"""
		Use /opt/vpn/response file to get request from Host (or priviledged user).
		"""
		with self.responseFile.open("r", encoding='utf-8') as f:
			status = f.read()
			return status == "up"
		return False
