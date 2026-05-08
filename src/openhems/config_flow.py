from homeassistant import config_entries
from .const import DOMAIN

class OpenHEMSConfigFlow(config_entries.ConfigFlow, domain="openhems"):
    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required("provider"): vol.In(["EDF", "Engie", "Autre"]),
                    vol.Optional("solar_power"): int,
                    vol.Optional("battery_capacity"): int,
                })
            )
        return self.async_create_entry(title="OpenHEMS", data=user_input)
