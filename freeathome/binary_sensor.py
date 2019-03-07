''' Support for Free@Home Binary devices like sensors, movement detectors '''
import logging
from homeassistant.components.binary_sensor import (BinarySensorDevice)
import custom_components.freeathome as freeathome

REQUIREMENTS =  ['slixmpp==1.4.2']

DEPENDENCIES = ['freeathome']

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, add_devices, discovery_info=None):
    """ setup """
    import custom_components.pfreeathome

    _LOGGER.info('FreeAtHome setup binary sensor')

    fah = hass.data[freeathome.DATA_MFH]

    devices = fah.get_devices('binary_sensor')

    for device, device_object in devices.items():
        add_devices([FreeAtHomeBinarySensor(device_object)])

class FreeAtHomeBinarySensor(BinarySensorDevice):
    ''' Interface to the binary devices of Free@Home '''
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
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    async def async_update(self):
        """Retrieve latest state."""
        self._state = (self.binary_device.state == '1')
