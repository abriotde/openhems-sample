"""
Thos module is used to monitor/drive VPN.
"""
import subprocess
import time
from pathlib import Path

class VpnDriver:
    """
    Abstract class for VPN Driver.
    """
    def test_vpn(self):
        """
        Test if the VPN is up.
        @return: bool : True if VPN is up, false else
        """
        raise NotImplementedError("test_vpn() not implemented")

    def start_vpn(self, start: bool = True):
        """
        Start/Stop the VPN.
        @param start: bool: if False stop the Wireguard's VPN else start it.
        """
        raise NotImplementedError("start_vpn() not implemented")

class VpnDriverWireguard(VpnDriver):
    """
    Start/stop/test a VPN Wireguard
    """
    def __init__(self, logger, vpn_interface="wgo"):
        self.vpn_interface = vpn_interface
        self.logger = logger

    def test_vpn(self):
        """
        Use 'ip a| grep "wg0:"' to test if Wireguard VPN is Up.
        We could use "wg show" but it need to be root
        @return: bool : True if VPN is up, false else
        """
        with subprocess.Popen(
            "ip a| grep '" + self.vpn_interface + ":'",
            shell=True, stdout=subprocess.PIPE
        ) as fd:
            vpn_interfaces = fd.stdout.read()
            vpn_interfaces = str(vpn_interfaces).strip()
            nb_interfaces = len(vpn_interfaces)
            ok = nb_interfaces > 3
            self.logger.info("VPN is %s", 'up' if ok else 'down')
            return ok
        return False

    def start_vpn(self, start: bool = True):
        """
        @param start: bool: if False stop the Wireguard's VPN else start it.
        """
        cmd = "wg-quick " + ("up" if start else "down") + " " + self.vpn_interface
        # Start the VPN
        with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE) as _:
            pass

class VpnDriverIncronServer(VpnDriver):
    """
    It's not a daemond, it use incrontab daemond to serve client.

    !!! WARNING !!!
     It is not thread safe, but as there should have only one client,
     and not so much request, it's enough and simple.
    """
    def __init__(self, logger, path_vpn="/data/vpn"):
        self.logger = logger
        self.path_vpn = Path(path_vpn)
        self.request_file = self.path_vpn / 'request'
        self.response_file = self.path_vpn / 'response'
        self.driver = VpnDriverWireguard(logger)

    def response(self, up=None):
        """
        Write VPN status on self.response_file.
        """
        if up is None:
            up = self.driver.test_vpn()
        msg = "up" if up else "down"
        with self.response_file.open("w", encoding='utf-8') as f:
            f.write(msg)
            self.logger.info("VPN Status = %s", msg)
            return up
        return ''

    def start_vpn(self, start:bool = True):
        """
        Start the VPN using 'driver'
        """
        self.logger.info("Start VPN")
        self.driver.start_vpn(start)
        self.test_vpn()

    def stop_vpn(self):
        """
        Stop the VPN using 'driver'
        """
        self.logger.info("Stop VPN")
        self.driver.start_vpn(False)
        self.test_vpn()

    def test_vpn(self):
        """
        Test the VPN using 'driver'
        """
        up = self.driver.test_vpn()
        response = self.response(up)
        self.logger.info("VPN Status = '%s'", response)
        return up

    def run(self):
        """
        The function is called, each time self.request_file is accessed.
        """
        with self.request_file.open("r", encoding='utf-8') as f:
            action = f.read().strip()
            if action == "start":
                self.start_vpn()
            elif action == "stop":
                self.stop_vpn()
            elif action == "test":
                self.test_vpn()
            else:
                self.logger.error("Uknwon VPN action : '%s'", action)

    def run_server(self):
        """
        Run a real server witch check the request file...
         It is not the goal but used when there is no incron
          (Debian Buleseye).
         It should be better to use FIFO...
         but won't be compatible with incron.
        """
        up = self.driver.test_vpn()
        last_action = "start" if up else "stop"
        while True:
            with self.request_file.open("r", encoding='utf-8') as f:
                action = f.read().strip()
                if last_action != action:
                    if action == "start":
                        self.start_vpn()
                    elif action == "stop":
                        self.stop_vpn()
                    elif action == "test":
                        up = self.test_vpn()
                    else:
                        self.logger.error("Uknwon VPN action : '%s'", action)
                    last_action = action
            time.sleep(10)

class VpnDriverIncronClient:
    """
    Used in docker container to start/stop/test host VPN
    Use shared repository beetwen Docker and Host /data:/opt.
    """
    def __init__(self, logger, path_vpn="/opt/vpn"):
        self.logger = logger
        self.path_vpn = Path(path_vpn)
        self.request_file = self.path_vpn / 'request'
        self.response_file = self.path_vpn / 'response'

    def start_vpn(self, start: bool = True):
        """
        Use /opt/vpn/request file to send request to Host (or priviledged user).
        @param start: bool: if False stop the Wireguard's VPN else start it.
        """
        request = "start" if start else "stop"
        with self.request_file.open("w", encoding='utf-8') as f:
            f.write(request)

    def test_vpn(self):
        """
        Use /opt/vpn/response file to get request from Host (or priviledged user).
        """
        with self.response_file.open("r", encoding='utf-8') as f:
            status = f.read()
            return status == "up"
        return False
