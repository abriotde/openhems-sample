#!/bin/env python
"""
Test and validation module for streamlit solution.
"""


import sys
from pathlib import Path
import logging
from time import sleep
import threading
from threading import Thread
import unittest

# pylint: disable=wrong-import-position, import-error
ROOT_PATH = Path(__file__).parents[0]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.modules.network.schedule import OpenHEMSSchedule
from openhems.modules.util import ProjectConfiguration
from openhems.unix_socket import UnixSocketServer
from openhems.modules.network.driver.fake_network import FakeNetwork
from openhems.modules.web import OpenhemsHTTPServer, OpenHEMSContext

logger = logging.getLogger(__name__)



def root_run(context:OpenHEMSContext):
    """
    Simulate core OpenHEMS process
    """
    socket = UnixSocketServer(context.schedule, context.network, context.logger)
    socket.start()
    try:
        for _ in range(3):
            print("Schedules:")
            for node_id, node in context.schedule.items():
                print(" - ", node_id, "-", node)
            sleep(10)
    except KeyboardInterrupt:
        socket.stop()
    socket.stop()

class TestStreamlit(unittest.TestCase):
    """
    Dummy test class to run Streamlit test without running the whole OpenHEMS application.
    """
    def test_streamlit(self):
        """
        Test function to run Streamlit app without running the whole OpenHEMS application.
        """
        # Create a dummy context with necessary attributes
        network = FakeNetwork(ProjectConfiguration())
        dummy_context = OpenHEMSContext(
            lock=threading.Lock(),
            schedule={"node_id": OpenHEMSSchedule(3600, "Test Schedule")},
            logger=logger,
            configurator=None,
            translations={"web": {"defaultTooltip": "Default: tooltip"}},
            vpnDriver=None,
            network=network
        )
        # Run the Streamlit app
        server = OpenhemsHTTPServer(
            mylogger=dummy_context.logger,
            schedule=dummy_context.schedule,
            warningMessages=[],
            port=8000,  # Default Streamlit port
            in_docker=False,
            configurator=dummy_context.configurator
        )
        t0 = Thread(target=root_run, args=[dummy_context], daemon=True)
        t0.start()
        server.run(test_mode=True)
        server.test()
        server.stop()
        t0.join(timeout=5)

if __name__ == '__main__':
    unittest.main()
