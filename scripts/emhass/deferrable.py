
class Deferrable:

	def __init__(self, nominal_power, duration_in_hours, start_timestep=0, end_timestep=0, constant = False, start_penalty = 0.0, as_semi_cont = True):
		self.power = nominal_power
		self.duration = duration_in_hours
		self.start_timestep = start_timestep
		self.end_timestep = end_timestep
		self.constant = constant
		self.start_penalty = start_penalty
		self.as_semi_cont = as_semi_cont

