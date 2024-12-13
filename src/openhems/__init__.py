"""
The openhems custom component.

This component aim to automate Home Energy Management using Home-Assistant.

Configuration:

To use the openhems component you will need to add the following to your
configuration.yaml file.

openhems:
"""

# https://github.com/home-assistant/example-custom-config/tree/master/custom_components
import logging
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

# The domain of your component. Should be equal to the name of your component.
DOMAIN = "openhems"
_LOGGER = logging.getLogger(__name__)

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
	"""Set up a skeleton component."""
	# States are in the format DOMAIN.OBJECT_ID.
	hass.states.set('openhems.ok', 'Works!')
	def openhems_web(call: ServiceCall) -> None:
		"""My first service."""
		_LOGGER.info('Received data', call.data)

	def openhems_core(call: ServiceCall) -> None:
		"""My first service."""
		_LOGGER.info('Received data', call.data)

	hass.services.register(DOMAIN, 'web', openhems_web)
	hass.services.register(DOMAIN, 'core', openhems_core)

	# Return boolean to indicate that initialization was successfully.
	return True
