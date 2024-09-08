""" Support for Free@Home switches """
import logging
from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices, discovery_info=None):
    """ switch specific code."""

    _LOGGER.info('FreeAtHome setup switch')

    sysap = hass.data[DOMAIN][config_entry.entry_id]

    devices = sysap.get_devices('switch')

    for device_object in devices:
        async_add_devices([FreeAtHomeSwitch(device_object)])


class FreeAtHomeSwitch(SwitchEntity):
    """ Free@home switch """
    switch_device = None
    _name = ''
    _state = None

    def __init__(self, device):
        self.switch_device = device
        self._name = self.switch_device.name
        self._state = self.switch_device.state

    @property
    def name(self):
        """Return the display name of this switch."""
        return self._name

    @property
    def device_info(self):
        """Return device id."""
        return self.switch_device.device_info

    @property
    def unique_id(self):
        """Return the ID """
        return self.switch_device.serialnumber + '/' + self.switch_device.channel_id

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state


    async def async_added_to_hass(self):
        """Register callback to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_update_ha_state(True)

        self.switch_device.register_device_updated_cb(after_update_callback)

    async def async_turn_on(self, **kwargs):
        """Instruct the switch to turn on."""

        await self.switch_device.turn_on()
        self._state = True

    async def async_turn_off(self, **kwargs):
        """Instruct the switch to turn off."""
        await self.switch_device.turn_off()
        self._state = False

    async def async_update(self):
        """Fetch new state data for this switch.
        This is the only method that should fetch new data for Home Assistant."""
        self._state = self.switch_device.is_on()