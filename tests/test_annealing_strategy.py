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
    Try test simulated annealing strategy
    """

    # pylint: disable=invalid-name
    def test_run_server(self):
        """
        Test if server start well with FakeNetwork adapter
        """
        configFile = utils.ROOT_PATH / "tests/data/openhems_fake4tests_annealing.yaml"
        self.init(configFile)
        self.loop()
        nodes_ids = ["pump", "car", "machine"]
        self.set_nodes_values(nodes_ids, scheduled_durations=[3600, 3600, 3600])
        # Simulated annealing is too random to check values.
        # But Genetic algorithm isn't.
        self.check_values(nodes_ids, [0, 0, 0], margin_power=3100)
        self.loop()
        self.check_values(nodes_ids, [280, 0, 800], margin_power=3100)

    # pylint: disable=invalid-name
    def test_xxx(self):
        """
        TODO: more tests
        """

if __name__ == '__main__':
    unittest.main()
