#!/usr/bin/env python3
"""
Test AnnealingStrategy class, 
"""
import sys
import unittest
from pathlib import Path
import logging
# pylint: disable=wrong-import-position, import-error
sys.path.append(str(Path(__file__).parents[0]))
import utils

logger = logging.getLogger(__name__)

class TestAnnealingStrategy(utils.TestStrategy):
    """
    Try test wall core server (OpenHEMS part, not web part)
    """

    def test_run_server(self):
        """
        Test if server start well with FakeNetwork adapter
        """
        config_file = utils.ROOT_PATH / "tests/data/openhems_fake4tests_solarnosell.yaml"
        self.init(config_file)
        nodes_ids = ["pump", "car", "machine"]
        self.check_values(nodes_ids, [0, 0, 0], margin_power=2100)
        self.loop()
        self.check_values(nodes_ids, [0, 0, 0])


    # pylint: disable=invalid-name
    def test_without_publicpowergrid(self):
        """
        Test without public power grid.
        """
        config_file = (utils.ROOT_PATH /
            "tests/data/openhems_fake4tests_solarnosell_withoutpublicpowergrid.yaml")
        self.init(config_file)
        nodes_ids = ["pump", "car", "machine"]
        self.check_values(nodes_ids, [0, 0, 0], margin_power=-300)
        self.loop()
        self.check_values(nodes_ids, [0, 0, 0])

if __name__ == '__main__':
    unittest.main()
