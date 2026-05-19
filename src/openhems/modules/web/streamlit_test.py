#!/bin/env python
"""
Test and validation module for streamlit solution.
"""


import sys
import os
import logging
from time import sleep
import threading
from threading import Thread

# pylint: disable=wrong-import-position
sys.path.append(os.path.dirname(__file__))
from openhems.modules.web import OpenHEMSSchedule
from openhems.modules.util import ProjectConfiguration
from openhems.modules.web.unix_socket import UnixSocketServer
from openhems.modules.network.driver.fake_network import FakeNetwork
from openhems.modules.web.Dashboard import OpenhemsHTTPServer2, OpenHEMSContext

logger = logging.getLogger(__name__)



def root_run(context):
    """
    Simulate core OpenHEMS process
    """
    socket = UnixSocketServer(context.schedule, context.lock, context.network, context.logger)
    socket.start()
    try:
        while True:
            print("Schedules:")
            for node_id, node in context.schedule.items():
                print(" - ", node_id, "-", node)
            sleep(10)
    except KeyboardInterrupt:
        socket.stop()

def streamlit_test():
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
    server = OpenhemsHTTPServer2(
        mylogger=dummy_context.logger,
        schedule=dummy_context.schedule,
        warningMessages=[],
        port=8000,  # Default Streamlit port
        inDocker=False,
        configurator=dummy_context.configurator
    )
    t0 = Thread(target=root_run, args=[dummy_context], daemon=True)
    t0.start()
    server.run()
    t0.join(timeout=5)


streamlit_test()
