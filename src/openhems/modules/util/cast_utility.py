"""
Usefull function for standard usages
"""

import json

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
				raise CastException("Unavailable value for '"+value+"'", 0)
			retValue = int(value)
		else:
			raise CastException("Impossible cast to int: Undefined algorythm : '"+type(value)+"'", 0)
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
		else:
			raise CastException("Impossible cast to bool: Undefined algorythm : '"+type(value)+"'", 0)
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
	def toTypeFloat(value):
		"""
		Convert to type float
		"""
		retValue = None
		if isinstance(value, (int, float)):
			retValue = value
		elif isinstance(value, str):
			if value.isnumeric():
				retValue = float(value)
			elif value=="unavailable":
				raise CastException("No value for '"+value+"'", 0)
			else:
				raise CastException("Incorect string value for  float: '"+value+"'", 0)
		else:
			raise CastException("Impossible cast to float: Undefined algorythm : '"+type(value)+"'", 0)
		return retValue

	@staticmethod
	def toTypeList(value):
		"""
		Convert to type list, raise CastException if it's impossible
		"""
		retValue = None
		if isinstance(value, list):
			retValue = value
		elif isinstance(value, str):
			if value[0] == "[":
				try:
					retValue = json.loads(value)
				except ValueError:
					retValue = [value]
			else:
				raise CastException("Incorect string value for  float: '"+value+"'", 0)
		else:
			raise CastException("Impossible cast to list: Undefined algorythm : '"+type(value)+"'", 0)
		return retValue

	@staticmethod
	def toType(destType, value):
		"""
		With Home-Assitant API we get all as string.
		 If it's power or other int value, we need to convert it.
		 We need to manage some incorrect value due to errors.
		"""
		retValue = None
		if destType is None:
			retValue = value
		elif destType=="int":
			retValue = CastUtililty.toTypeInt(value)
		elif destType=="bool":
			retValue = CastUtililty.toTypeBool(value)
		elif destType=="str":
			retValue = CastUtililty.toTypeStr(value)
		elif destType=="float":
			retValue = CastUtililty.toTypeFloat(value)
		elif destType=="list":
			retValue = CastUtililty.toTypeList(value)
		else:
			raise CastException(".toType("+str(destType)+","+str(value)+") : Unknwon type", 0)
		return retValue
