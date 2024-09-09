from datetime import datetime, timedelta
import time
import re
import logging
from modules.network.network import OpenHEMSNetwork
from .energy_strategy import EnergyStrategy
from .offpeak_manager import OffPeakManager
import yaml
yaml_conf = os.path.dirname(__file__)+"/../../../data/edf.yaml"


class Pricing:
	def getPricing(self):
		print("Pricing : TODO implement a subclass")
	

class EDFTempoPricing(Pricing)0:
	"""
	This is in case we just base on "off-peak" range hours to control output. Classic use-case is some grid contract (Like Tempo on EDF).
	The strategy is to switch on electric devices only on "off-peak" hours with check to not exceed authorized max consumption
	"""
	def __init__(self, network: OpenHEMSNetwork, device_id="sensor.rte_tempo", subcribed_power=6):
		self.logger = logging.getLogger(__name__)
		self.device_id = device_id
		self.offpeakHoursRanges=[["22:00:00","06:00:00"]]
		self.logger.info("EDFTempoPricing(",device_id,", "+str(offpeakHoursRanges)+")")
		self.network = network
		self.offpeakManager = OffPeakManager(offpeakHoursRanges)
		self.cur_daycolor = SourceFeeder(device_id+"_couleur_actuelle_visuel", network.network_updater, "str")
		self.next_daycolor = SourceFeeder(device_id+"_prochaine_couleur_visuel", network.network_updater, "str")
		conf = yaml.load(yaml_conf, Loader=yaml.FullLoader)
		self.pricings = conf["tempo"]

	def getPrice(self, color, inOffpeakRange):
		prices = self.pricings.get(color.lower(), [0,0])
		idx = (0 if inOffpeakRange else 1)
		price = prices[idx]
		if price==0:
			self.logger.warning("EDFTempoPricing : Fail get price for '"+(curcolor.lower())+"'.")
		return price

	def getPricing(self):
		pricing = []
		datetimeDayChange = dt = datetime.now()
		lastdate = curdate = dt.strftime("%Y%m%d")
		while True:
			if dt>=datetimeDayChange: # We change color
				if lastdate==curdate:
					curcolor = self.next_daycolor.getValue()
					if int(dt.strftime("%H%M%S"))<060000:
						ndt = dt
					else:
						ndt = dt + timedelta(days=1)
					datetimeDayChange = datetime(ndt.year, ndt.month, ndt.day, 6, 0, 0, 0)
					lastdate = datetimeDayChange.strftime("%Y%m%d")
				else:
					return pricing
			inOffpeakRange = self.offpeakManager.inOffpeakRange(dt)
			rangeEnd = self.offpeakManager.getRangeEnd()
			price = self.getPrice(curcolor, inOffpeakRange)
			pricing.push((dt, price, rangeEnd))
			dt = rangeEnd + datetime.timedelta(0,1)
		
		
		

class EDFHeuresCreusesPricing(Pricing):
	def __init__(self, subcribed_power=6):
		self.logger = logging.getLogger(__name__)
		self.offpeakHoursRanges=[["22:00:00","06:00:00"]]
		self.logger.info("EDFHeuresCreusesPricing("+str(offpeakHoursRanges)+")")
		self.offpeakManager = OffPeakManager(offpeakHoursRanges)
		conf = yaml.load(yaml_conf, Loader=yaml.FullLoader)
		self.pricings = conf["standard"]

	def getPricing(self):
		

	
