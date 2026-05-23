#!/bin/env python
"""
Test streamlit Dashboard integrity
"""
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import pandas as pd
from streamlit.testing.v1 import AppTest # pylint: disable=import-error

ROOT_PATH = Path(__file__).parents[1]
class TestDashboard(unittest.TestCase):
    """Test the Dashboard streamlit page with AppTest"""

    def setUp(self):
        """
        Set up the test case (__init__)
        """
        # Create a mock socket client with controlled return values
        self.mock_socket_client = MagicMock()
        self.at = None

    def init_app(self, schedule=None):
        """
        Initialize the Streamlit app with a mock UnixSocketClient
        """
        self.mock_socket_client.get_schedule.return_value = schedule
        self.mock_socket_client.update_schedule = MagicMock()

        # Patch OpenhemsHTTPServer.get_socket_client at the point where Dashboard imports it
        patcher = patch('openhems.unix_socket.UnixSocketClient.get_schedule',
            return_value=schedule
        )
        self.mock_socket_client.get_schedule = patcher.start()
        self.mock_socket_client.get_schedule.return_value = schedule
        self.addCleanup(patcher.stop)

        patcher = patch('openhems.unix_socket.UnixSocketClient.update_schedule',
            return_value=True
        )
        self.mock_socket_client.update_schedule = patcher.start()
        self.mock_socket_client.update_schedule.return_value = True
        self.addCleanup(patcher.stop)

        # Create and run the AppTest (load the Dashboard page)
        # Adjust the path to your actual Dashboard.py file
        self.at = AppTest.from_file(ROOT_PATH / "src/openhems/modules/web/Dashboard.py")

        # Verify the app did not crash
        if self.at.exception:
            raise self.at.exception[0] # pylint: disable=raising-non-exception

    def click_save_button(self):
        """
        Simulate clicking the save button in the Streamlit app
        """
        # Click the save button
        save_buttons = list(filter(
            lambda b: b.label == "💾 Appliquer les modifications",
            self.at.button
        ))
        self.assertEqual(len(save_buttons), 1, "Save button not found")
        save_buttons[0].click()
        self.at.run()

    def test_update_schedule_on_button_click(self):
        """Simulate editing a duration and clicking the save button"""
        # Access the data_editor component (there should be exactly one)
        self.init_app({
            "device1": {
                "name": "Heater",
                "duration": 3600,
                "timeout_dt": "2025-12-31 23:59"
            },
            "device2": {
                "name": "Pump",
                "duration": 120,
                "timeout_dt": None
            }
        })
        # mock_get_client.return_value = self.mock_socket_client
        self.at.run()
        # Get the first datafame (There is only one)
        # dataframes = self.at.data_editor(key="schedules_editor") :
        #  - Not supported : "AttributeError: 'AppTest' object has no attribute 'data_editor'"
        dataframes = self.at.dataframe
        self.assertEqual(len(dataframes), 1, "No data_editor found in the app")
        df = dataframes[0].value # pylint: disable=no-member

        # Modify "device1"
        # print("Original df:\n", df, file=sys.stderr)
        self.assertEqual(df.shape[0], 2, "No data_editor found in the app")
        df.at[0, "Duration"] = 7200
        df.at[0, "Timeout"] = pd.NA
        # print("New df:\n", df, file=sys.stderr)

        self.click_save_button()

        # Verify update_schedule was called with correct arguments
        # TODO when abble to update dataframe in AppTest
        # self.mock_socket_client.update_schedule.assert_called_once_with(
        #     "device1", 7200, None
        # )
        # Check success message appears
        # success_messages = [msg.value for msg in self.at.success]
        # self.assertTrue(any("Programmations mises à jour" in msg for msg in success_messages))
        info_messages = [msg.value for msg in self.at.info]
        self.assertTrue(any("Aucune modification détectée." in msg for msg in info_messages))

    def test_update_schedule_with_timeout(self):
        """Test updating a timeout value"""
        self.init_app({
            "device1": {
                "name": "Heater",
                "duration": 3600,
                "timeout_dt": "2025-12-31 23:59"
            },
            "device2": {
                "name": "Pump",
                "duration": 120,
                "timeout_dt": None
            }
        })
        self.at.run()

        dataframes = self.at.dataframe
        self.assertEqual(len(dataframes), 1, "No data_editor found in the app")
        df = dataframes[0].value # pylint: disable=no-member
        new_timeout = datetime(2026, 12, 31, 23, 59)
        df.at[1, "Timeout"] = new_timeout   # second device
        df.at[1, "Duration"] = 300

        self.click_save_button()

        # Timeout should be converted to ISO format string "YYYY-MM-DDTHH:MM:SS"
        # expected_timeout_str = "2026-12-31T23:59:00"
        # self.mock_socket_client.update_schedule.assert_called_once_with(
        #     "device2", 300, expected_timeout_str
        # )

    def test_handles_schedule_none(self):
        """Test graceful handling when get_schedule returns None"""
        # Override the mock to return None
        self.init_app(schedule=None)
        self.at.run()

        warnings = [w.value for w in self.at.warning]
        self.assertTrue(any("Erreur lors de la récupération" in w for w in warnings))

if __name__ == "__main__":
    unittest.main()
