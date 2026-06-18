
class DangerousStateException(Exception):
	"""
	Raised on dangerous electricty state, like impossible, risk of electrical short circuit or fire
	(Network is not equilibrated)
	"""
	def __init__(self, message, alertType):
		self.message = message
		self.type = alertType
