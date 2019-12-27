""" Support for Free@Home Binary devices like sensors, movement detectors """
import logging
from homeassistant.components.binary_sensor import (BinarySensorDevice)
import custom_components.freeathome as freeathome

REQUIREMENTS = ['slixmpp==1.4.2']

DEPENDENCIES = ['freeathome']

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """ setup """

    _LOGGER.info('FreeAtHome setup binary sensor')

    fah = hass.data[freeathome.DATA_MFH]

    devices = fah.get_devices('binary_sensor')

    for device, device_object in devices.items():
        async_add_devices([FreeAtHomeBinarySensor(device_object)])


class FreeAtHomeBinarySensor(BinarySensorDevice):
    """ Interface to the binary devices of Free@Home """
    _name = ''
    binary_device = None
    _state = None

    def __init__(self, device):
        self.binary_device = device
        self._name = self.binary_device.name
        self._state = self.binary_device.state

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return the ID """
        return self.binary_device.device_id

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
