#!/usr/bin/env python3
"""
Check common functionnality
 of openhems.modules.energy_strategy.offpeak_strategy.OffPeakStrategy
"""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import logging
import yaml
# pylint: disable=wrong-import-position
# pylint: disable=import-error
ROOT_PATH = Path(__file__).parents[1]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.modules.contract import (
    RTETempoContract
)

logger = logging.getLogger(__name__)


class TestContractModule(unittest.TestCase):
    """
    Check common functionnality of contract module (openhems.modules.util)
    """
    DATETIME_STR_FORMAT = "%Y-%m-%d %H:%M:%S"
    DATE_STR_FORMAT = "%Y-%m-%d"
    _colors = None

    def get_contract_rtetempo(self):
        """
        Return a standard RteTempoContract
        """
        contract = RTETempoContract(color=None, colorNext=None,
                offpeakprices={"bleu":0.1, "blanc":0.2, "rouge":0.3},
                peakprices = {"bleu":0.4, "blanc":0.5, "rouge":0.6})
        return contract

    def get_date(self, color):
        """
        Return a date with the color
        """
        if self._colors is None:
            current_date = datetime.now()
            conf_path = Path(__file__).parent / 'data' / 'contract_rtetempo_data.yaml'
            conf_date = datetime.strptime("1970-01-01 01:00:00", self.DATETIME_STR_FORMAT)
            conf = {}
            timedelta_1year = timedelta(days=360)
            if conf_path.exists():
                with conf_path.open('r', encoding="utf-8") as f:
                    conf = yaml.safe_load(f)
                    conf_date = conf['date']
            # callApiRteTempo() is valid only on last year.
            maxdate = conf_date + timedelta_1year
            if current_date >= maxdate: # more than 30 days, we refresh data
                # Without valid saved conf,
                # we search for the last 3 colors before current date,
                # and save them in conf file with the date of the oldest color
                colors = {}
                conf_date = current_date - timedelta(days=1)
                min_date = current_date - timedelta_1year
                contract = self.get_contract_rtetempo()
                while conf_date >= min_date and len(colors)<3:
                    date_str = conf_date.strftime(self.DATE_STR_FORMAT)
                    c = contract.callApiRteTempo(date_str)
                    colors[c] = date_str
                    conf_date -= timedelta(days=1)
                conf = {'date': conf_date, 'colors': colors}
                with conf_path.open(mode='w', encoding="utf-8") as f:
                    yaml.dump(conf, f)
            self._colors = conf['colors']
        return self._colors[color]

    # pylint: disable=invalid-name
    def test_rtetempo_colors(self):
        """
        Test default values/overridden/singleton/unknown key
        """
        contract = self.get_contract_rtetempo()
        # print("test_configurationsManager()")
        date_bleu = self.get_date("bleu")
        date_blanc = self.get_date("blanc")
        date_rouge = self.get_date("rouge")
        datetime_rouge = datetime.strptime(date_rouge + " 01:01:01", self.DATETIME_STR_FORMAT)
        before_date_rouge = (datetime_rouge - timedelta(days=1)).strftime(self.DATE_STR_FORMAT)
        self.assertEqual(contract.callApiRteTempo(date_bleu), "bleu")
        self.assertEqual(contract.callApiRteTempo(date_blanc), "blanc")
        self.assertEqual(contract.callApiRteTempo(date_rouge), "rouge")
        mydate = datetime.strptime(date_rouge + " 05:59:54", self.DATETIME_STR_FORMAT)
        self.assertEqual(contract.getColorDate(mydate), before_date_rouge)
        # test caches
        c1 = contract.getNextColor()
        c2 = contract.getNextColor()
        self.assertEqual(c1, c2)
        c1 = contract.getCurColor()
        c2 = contract.getCurColor()
        self.assertEqual(c1, c2)

    def test_rtetempo_hoursranges(self): # pylint: disable=too-many-locals
        """
        Test RteContract.getHoursRanges() change .
        Test HoursRanges change when occure timeout/timeStart.
        """
        contract = self.get_contract_rtetempo()
        date_rouge = self.get_date("rouge")
        datetime_rouge = datetime.strptime(date_rouge + " 01:01:01", self.DATETIME_STR_FORMAT)
        before_date_rouge = (datetime_rouge - timedelta(days=1)).strftime(self.DATE_STR_FORMAT)
        after_date_rouge = (datetime_rouge + timedelta(days=1)).strftime(self.DATE_STR_FORMAT)
        datetimes = [
            (date_rouge + " 06:00:00", True),
            (date_rouge + " 06:00:01", False),
            (date_rouge + " 23:59:59", True),
            (after_date_rouge + " 00:00:00", True),
            (after_date_rouge + " 00:00:01", True),
            (after_date_rouge + " 05:59:59", True)
        ]
        ok = False
        for dt, off in datetimes:
            mydate = datetime.strptime(dt, self.DATETIME_STR_FORMAT)
            hoursRange = contract.getHoursRanges(now=None, attime=mydate)
            # print("For dt=", dt, "Hours Range:", hoursRange, file=sys.stderr)
            start = hoursRange.timeStart.strftime(self.DATETIME_STR_FORMAT)
            self.assertEqual(start, date_rouge + " 06:00:00", "Wrong timeStart")
            end = hoursRange.timeout.strftime(self.DATETIME_STR_FORMAT)
            self.assertEqual(end, after_date_rouge + " 06:00:00", "Wrong timeout")
            inoffpeak, rangeEnd, cost = hoursRange.checkRange(mydate)
            self.assertEqual(inoffpeak, off, "In off-peak for " + dt)
            if inoffpeak:
                self.assertEqual(cost, 0.3, "cost for " + dt)
            else:
                self.assertEqual(cost, 0.6,  "cost for " + dt)
            if not ok: # Test only once
                ok = True
                # test checkRange() when occure timeout
                clock = after_date_rouge + " 07:00:00"
                mydate = datetime.strptime(clock, self.DATETIME_STR_FORMAT)
                inoffpeak, rangeEnd, cost = hoursRange.checkRange(mydate)
                rangeEnd = rangeEnd.strftime(self.DATETIME_STR_FORMAT)
                self.assertFalse(inoffpeak)
                self.assertEqual(rangeEnd, after_date_rouge + " 22:00:00", "Wrong range end")
                self.assertLess(cost, 0.6,  "cost for " + clock)
                # test checkRange() when occure timeStart
                mydate = datetime.strptime(
                    before_date_rouge + " 23:00:00",
                    self.DATETIME_STR_FORMAT
                )
                inoffpeak, rangeEnd, cost = hoursRange.checkRange(mydate)
                rangeEnd = rangeEnd.strftime(self.DATETIME_STR_FORMAT)
                self.assertTrue(inoffpeak, "In off-peak of 23:00:00")
                self.assertEqual(rangeEnd, date_rouge + " 06:00:00", "off-peak range end")
                self.assertLess(cost, 0.3, "off-peak price red")

if __name__ == '__main__':
    unittest.main()
