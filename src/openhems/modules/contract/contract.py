"""
Main and Generic classes to manage contracts
"""
import logging
from openhems.modules.util import ConfigurationException, CastException
from .rte_contract import (
	RTETempoContract, RTEHeuresCreusesContract, RTETarifBleuContract
)
from .generic_contract import GenericContract


# pylint: disable=too-few-public-methods
class Contract:
	"""
	Main super lass for contracts
	"""
	logger = logging.getLogger(__name__)

	@staticmethod
	def getContract(contractDict, genericConfiguration, networkUpdater):
		"""
		Method to return a contract from YAML configuration dict
		"""
		classname = contractDict.get("class", None)
		if classname is None:
			msg = "Missing mandatory 'class' atribute for contract."
			raise ConfigurationException(msg)
		try:
			classname = classname.lower()
			contract = None
			if classname.endswith("contract"):
				classname  = classname[:-8]
			if classname.startswith("rte"):
				if classname=="rtetempo":
					contract = RTETempoContract.fromdict(contractDict, genericConfiguration, networkUpdater)
				elif classname=="rteheurescreuses":
					contract = RTEHeuresCreusesContract.fromdict(contractDict, genericConfiguration)
				elif classname=="rtetarifbleu":
					contract = RTETarifBleuContract.fromdict(contractDict, genericConfiguration)
			elif classname=="generic":
				contract = GenericContract.fromdict(contractDict, genericConfiguration)
			# Contract.logger.info("Contract: %s", contract)
			return contract
		except CastException as e:
			raise ConfigurationException(e.message) from e

	def getPrice(self, now=None):
		"""
		Return the electrycity cost. Should be overload	
		"""
		del now
		self.logger.warning("Function getElectricityCost() should be overload")
		return 1
