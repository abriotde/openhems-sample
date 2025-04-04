"""
Usefull function for standard usages
"""

import json
from datetime import datetime, timedelta
import re

REGEXP_TIME = re.compile("^([0-9]{1,2})(h|:)([0-9]{1,2})((m|:)[0-9]{2}(s?))?")
REGEXP_FLOAT = re.compile("^[0-9]+(.[0-9]*)??$")


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
			retValue = int(float(value)) # int("0.0") crash while float("0") don't...
		else:
			raise CastException("Impossible cast to int: Undefined algorythm : '"+str(type(value))+"'", 0)
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
			val = REGEXP_FLOAT.match(value)
			if val:
				retValue = float(value)
			elif value=="unavailable":
				raise CastException("No value for '"+value+"'", 0)
			else:
				raise CastException("Incorect string value for  float: '"+value+"'", 0)
		else:
			raise CastException("Impossible cast to float: Undefined algorythm : '"+type(value)+"'", 0)
		return retValue

	@staticmethod
	def toTypeDatetime(value, nowtime:datetime=None):
		"""
		Convert to type string
		"""
		if isinstance(value, datetime):
			retValue = value
		elif isinstance(value, str):
			vals = REGEXP_TIME.match(value)
			if vals: # Time without date, set date to curdate() and get next time
				h = int(vals[1])
				m = int(vals[3])
				s = 0 # TODO : extract
				if nowtime is None:
					nowtime = datetime.now()
				retValue = nowtime.replace(hour=h, minute=m, second=s)
				if nowtime>retValue:
					retValue = retValue + timedelta(days=1)
			else:
				# TODO datetime as str
				raise CastException("Impossible cast to datetime from string "+value, 0)
		else:
			raise CastException("Impossible cast to datetime for type "+(type(value).__name__), 0)
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
					value2 = value.replace('[', '["').replace(']', '"]').replace(',', '","')
					try:
						retValue = json.loads(value2)
					except ValueError:
						retValue = [value]
			else:
				raise CastException("Incorect string value for  float: '"+value+"'", 0)
		else:
			raise CastException("Impossible cast to list: Undefined algorythm : '"+str(type(value))+"'", 0)
		return retValue

	@staticmethod
	def toTypeDict(value):
		"""
		Convert to type list, raise CastException if it's impossible
		"""
		if isinstance(value, dict):
			retValue = value
		else:
			raise CastException("Impossible to cat "+str(value)+" to type dict.", 0)
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
		elif value is None or value=="None":
			return None
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
		elif destType=="datetime":
			retValue = CastUtililty.toTypeDatetime(value)
		elif destType=="dict":
			retValue = CastUtililty.toTypeDict(value)
		else:
			raise CastException(".toType("+str(destType)+","+str(value)+") : Unknwon type", 0)
		return retValue
