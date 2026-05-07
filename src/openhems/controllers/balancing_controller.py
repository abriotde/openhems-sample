
class BalancingController(Controller):
    """Règle les conflits entre les demandes des autres contrôleurs."""
    
    def run(self, context):
        # Par défaut, on prend la demande la plus forte en décharge
        # Mais on peut ajouter des règles: ne pas décharger si SOC < 20%
        if context.battery_soc < 20:
            context.battery_discharge_power = 0
        # Envoyer la consigne finale à Home Assistant
        context.set_battery_power(context.battery_discharge_power)

