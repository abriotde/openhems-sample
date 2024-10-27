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
	start_timestep = 0
	end_timestep = 0
	constant = False
	start_penalty: float = 0.0
	as_semi_cont: bool = True
