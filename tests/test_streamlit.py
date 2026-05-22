#!/bin/env python
"""
Test and validation module for streamlit solution.
"""


import sys
from pathlib import Path
import logging
from time import sleep
from threading import Thread
import unittest
from streamlit.testing.v1 import AppTest

# pylint: disable=wrong-import-position, import-error
ROOT_PATH = Path(__file__).parents[1]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.modules.network.schedule import OpenHEMSSchedule
from openhems.modules.util import ProjectConfiguration
from openhems.unix_socket import UnixSocketServer
from openhems.modules.network.driver.fake_network import FakeNetwork
from openhems.modules.web import OpenhemsHTTPServer, OpenHEMSContext

logger = logging.getLogger(__name__)



def root_run(context:OpenHEMSContext, infinity=False):
    """
    Simulate core OpenHEMS process
    """
    socket = UnixSocketServer(
        schedule=context.schedule, network=context.network,
        logger=context.logger
    )
    socket.start()
    try:
        n_loop = 3
        sleep_duration = 3
        if infinity:
            n_loop = 100000
            sleep_duration = 20
        for _ in range(n_loop):
            print("Schedules:")
            for node_id, node in context.schedule.items():
                print(" - ", node_id, "-", node)
            sleep(sleep_duration)
    except KeyboardInterrupt:
        socket.stop()
    print("Root_run OK.", file=sys.stderr)
    socket.stop()

class TestStreamlit(unittest.TestCase):
    """
    Dummy test class to run Streamlit test without running the whole OpenHEMS application.
    """
    def init(self, network=None, infinity=False):
        self.http_path = ROOT_PATH / "src" / "openhems" / "modules" / "web"
        if network is None:
            network = FakeNetwork(ProjectConfiguration())
        self.network = network
        dummy_context = OpenHEMSContext(
            schedule={"node_id": OpenHEMSSchedule(3600, "Test Schedule")},
            logger=logger,
            configurator=None,
            translations={"web": {"defaultTooltip": "Default: tooltip"}},
            vpnDriver=None,
            network=self.network
        )
        # Run the Streamlit app
        self.http_server = OpenhemsHTTPServer(
            logger=dummy_context.logger,
            schedule=dummy_context.schedule,
            warning_messages=[],
            port=8000,  # Default Streamlit port
            in_docker=False,
            configurator=dummy_context.configurator
        )
        self.core_thread = Thread(target=root_run, args=[dummy_context, infinity], daemon=True)
        self.core_thread.start()

    def stop(self):
        """
        Stop the test.
        """
        self.core_thread.join(timeout=60)
        self.http_server.stop()

    def xtest_streamlit(self):
        """
        Test function to run Streamlit app without running the whole OpenHEMS application.
        """
        # Create a dummy context with necessary attributes
        self.init()
        self.http_server.run(test_mode=True)
        self.http_server.test()
        self.stop()

    def test_dashboard(self):
        """
        Test function to run the dashboard without running the whole OpenHEMS application.
        """
        self.init()
        at = AppTest.from_file(self.http_path / "Dashboard.py").run()
        assert not at.exception
        self.assertEqual(at.get_element("h1").text(), "OpenHEMS Dashboard")
        self.assertIn("Default: tooltip", at.get_element("#tooltip").text())
        self.stop()



if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        test = TestStreamlit()
        test.init(infinity=True)
        test.http_server.run(test_mode=True)
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            test.stop()
    else:
        unittest.main(argv=[sys.argv[0], "TestStreamlit.test_dashboard"])
