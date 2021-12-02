""" Support for Free@Home Binary devices like sensors, movement detectors """
import logging
from homeassistant.components.binary_sensor import (BinarySensorEntity)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_devices, discovery_info=None):
    """ setup """

    _LOGGER.info('FreeAtHome setup binary sensor')

    fah = hass.data[DOMAIN][config_entry.entry_id]

    devices = fah.get_devices('binary_sensor')

    for device_object in devices:
        async_add_devices([FreeAtHomeBinarySensor(device_object,hass)])


class FreeAtHomeBinarySensor(BinarySensorEntity):
    """ Interface to the binary devices of Free@Home """
    _name = ''
    binary_device = None
    _state = None
    _hass = None

    def __init__(self, device, hass):
        self.binary_device = device
        self._name = self.binary_device.name
        self._state = (self.binary_device.state == '1')
        self._hass = hass

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def device_info(self):
        """Return device id."""
        return self.binary_device.device_info

    @property
    def unique_id(self):
        """Return the ID """
        return self.binary_device.serialnumber + '/' + self.binary_device.channel_id

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    async def async_added_to_hass(self):
        """Register callback to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_update_ha_state(True)

        self.binary_device.register_device_updated_cb(after_update_callback)

    async def async_update(self):
        """Retrieve latest state."""

        self._state = (self.binary_device.state == '1')
        _LOGGER.info('update sensor')

        eventdata = {
            "name"        : self._name,
            "serialnumber": self.binary_device.serialnumber,
            "unique_id"   : self.unique_id,
            "state"       : self._state,
            "command"     : "pressed"
        }
        self._hass.bus.async_fire("freeathome_event", eventdata)
