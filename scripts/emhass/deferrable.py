"""
Custom class to simplify emhass module live modifications.
"""

import dataclasses

@dataclasses.dataclass
class Deferrable:
	"""
	Custom class to simplify emhass module live modifications.
	"""
	power: float # Nominal power
	duration: int # Duration in seconds
	startTimestep = 0
	endTimestep = 0
	constant = False
	startPenalty: float = 0.0
	asSemiCont: bool = True
