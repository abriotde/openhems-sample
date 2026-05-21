"""
Utils classes for tests
"""
import sys
import unittest
import datetime
import logging
from pathlib import Path
# pylint: disable=wrong-import-position, import-error
ROOT_PATH = Path(__file__).parents[2]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.main import OpenHEMSApplication
from openhems.modules.util import DATETIME_PRINT_FORMAT

logger = logging.getLogger(__name__)

class TestStrategy(unittest.TestCase):
    """
    Class to factorize code for test strategies
    """
    # pylint: disable=attribute-defined-outside-init
    def init(self, config_file, now=None):
        """
        Init the application
        """
        # pylint: disable=attribute-defined-outside-init
        self.app = OpenHEMSApplication(config_file)
        self.nodes = {}
        self._loop_delay = 1
        if now is None:
            now = datetime.datetime.now()
        self._now = now
        if self.app is None or self.app.server is None:
            return None
        self.app.server.allowSleep = False
        for node in self.get_network().getAll("out"):
            logger.info("Node: %s is on:%s", node, node.isOn())
            self.assertFalse(node.isOn())
            self.nodes[node.id] = node
        self.app.server.loop(now)
        print("Network is : ", self.get_network())
        return self.nodes

    def loop(self, loop_delay=None, now=None):
        """
        If set now, we jump to now
        Else by default loop_delay is double at each loop
         it give unique loop
        """
        if now is None:
            if loop_delay is None:
                loop_delay = self._loop_delay
            # print("loop_delay:",loop_delay)
            self._now += datetime.timedelta(seconds=loop_delay)
        else:
            if loop_delay is not None:
                self._loop_delay = loop_delay
            else:
                self._loop_delay = (now - self._now).total_seconds()
            self._now = now
        logger.debug("Time: %s, lastloop: %s s",
            self._now.strftime(DATETIME_PRINT_FORMAT), self._loop_delay)
        self.app.server.loop(self._now)
        self._loop_delay *= 2
        return self.nodes


    def set_nodes_values(self, nodes_ids,
            scheduled_durations=None,
            scheduled_timeout=None,
            switch_on=None):
        """
        Set values of nodes
        """
        for i, node_id in enumerate(nodes_ids):
            node = self.nodes.get(node_id)
            if node is not None:
                if switch_on is not None:
                    node.switchOn(switch_on[i])
                if scheduled_durations is not None:
                    node.getSchedule().duration = scheduled_durations[i]
                if scheduled_timeout is not None:
                    node.getSchedule().timeout = scheduled_timeout[i]
            else:
                print(f"Node {node_id} not found in nodes")

    def check_values(self, nodes_ids, values,* ,
            margin_power=None,
            scheduled_durations=None,
            isOn=None):
        """
        Check values of nodes
        """
        for i, node_id in enumerate(nodes_ids):
            node = self.nodes.get(node_id)
            self.assertEqual(node.getCurrentPower(), values[i])
            if scheduled_durations is not None:
                schedule = node.getSchedule()
                self.assertEqual(schedule.duration, scheduled_durations[i])
            if isOn is not None:
                self.assertEqual(node.isOn(), isOn[i])
        if margin_power is not None:
            self.assertEqual(self.get_network().getMarginPowerOn(), margin_power)

    def get_network(self):
        """
        Return network
        """
        return self.app.server.network
