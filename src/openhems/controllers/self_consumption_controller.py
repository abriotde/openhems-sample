

class SelfConsumptionController(Controller):
    """Favorise l'autoconsommation en déchargeant la batterie si surplus exporté."""
    
    def run(self, context):
        if context.grid_export_power > 100:   # On exporte trop
            # Demander à la batterie de se décharger pour réduire l'export
            context.battery_discharge_power = min(
                context.grid_export_power,
                context.max_battery_power
            )
        else:
            context.battery_discharge_power = 0

