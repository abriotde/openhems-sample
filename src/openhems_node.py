
from enum import Enum

class OpenHEMSNode:
	@staticmethod
	def create(elem: dict):
		id = elem['id']
		use = elem['use']
		type = elem['type']
		o = OpenHEMSNode(id, use, type)

class InOutNode(OpenHEMSNode):
	def __init__(self, id, maxPower, minPower, 
			  isAutoAdatative: bool, isControlable: bool, isModulable: bool, isCyclic: bool) -> None:
		self.id = id
		self.maxPower = maxPower
		self.minPower = minPower
		self.isAutoAdatative = isAutoAdatative
		self.isControlable = isControlable
		self.isModulable = isModulable
		self.isCyclic = isCyclic
	
	def checkConstraints(self):
		pass

class PublicPowerGrid(InOutNode):
	def __init__(self, maxPower, minPower) -> None:
		self.isAutoAdatative = True
		self.isControlable = True
		self.isModulable = False

class RTETempoContract(PublicPowerGrid):
	def __init__(self, maxPower, minPower) -> None:
		self.isAutoAdatative = True
		self.isControlable = True
		self.isModulable = False

class Switch(InOutNode):
	def __init__(self, maxPower, minPower) -> None:
		self.isControlable = True
		self.isModulable = False

class CarCharger(Switch):
	def __init__(self, maxPower, minPower, capacity) -> None:
		assert minPower<=0 and maxPower<=0
		self.isControlable = True
		self.isModulable = False

class WaterHeater(InOutNode):
	def __init__(self, maxPower, minPower, capacity) -> None:
		assert minPower<=0 and maxPower<=0
		self.isControlable = True
		self.isModulable = True

class Battery(Switch):
	def __init__(self, maxPower, minPower, capacity) -> None:
		self.isControlable = True
		self.isModulable = False

class SolarPanel(InOutNode):
	def __init__(self, maxPower, minPower, capacity) -> None:
		assert minPower>=0 and maxPower>=0
		self.isControlable = False
		self.isModulable = False

	def __init__(self, id, use, type) -> None:
		pass