"""
Usefull function for standard usages
"""

import os

class CastException(Exception):
	"""
	Custom Home-Assitant excepton to be captured.
	"""
	def __init__(self, message, defaultValue):
		self.message = message
		self.defaultValue = defaultValue

class CastUtililty:
	"""
	Usefull function to do something like a cast : Convertion of types
	"""
	@staticmethod
	def toTypeInt(value):
		"""
		Convert to type integer
		"""
		retValue = None
		if isinstance(value, int):
			retValue = value
		elif isinstance(value, str):
			if value=="unavailable":
				raise CastException("WARNING : Unknown value for '"+value+"'", 0)
			retValue = int(value)
		return retValue
	@staticmethod
	def toTypeBool(value):
		"""
		Convert to type boolean
		"""
		retValue = None
		if isinstance(value, int):
			retValue = value>0
		elif isinstance(value, str):
			retValue = value.lower() in ["on", "true", "1", "vrai"]
		elif isinstance(value, bool):
			retValue = value
		return retValue
	@staticmethod
	def toTypeStr(value):
		"""
		Convert to type string
		"""
		if isinstance(value, int):
			retValue = str(value)
		elif isinstance(value, str):
			retValue = value
		else:
			retValue = str(value)
		return retValue

	@staticmethod
	def toType(destType, value):
		"""
		With Home-Assitant API we get all as string.
		 If it's power or other int value, we need to convert it.
		 We need to manage some incorrect value due to errors.
		"""
		retValue = None
		if destType=="int":
			retValue = CastUtililty.toTypeInt(value)
		elif destType=="bool":
			retValue = CastUtililty.toTypeBool(value)
		elif destType=="str":
			retValue = CastUtililty.toTypeStr(value)
		else:
			print(".toType(",destType,",",value,") : Unknwon type")
			os._exit(1)
		return retValue
