
class PeakShavingController(Controller):
    """Limite la puissance appelée au réseau."""
    
    def __init__(self, name, peak_limit_w=5000, **kwargs):
        super().__init__(name, **kwargs)
        self.peak_limit_w = peak_limit_w
    
    def run(self, context):
        if context.grid_import_power > self.peak_limit_w:
            excess = context.grid_import_power - self.peak_limit_w
            context.battery_discharge_power = min(excess, context.max_battery_power)

