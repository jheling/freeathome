""" Support for Free@Home lights dimmers """
import logging
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, Light)

import custom_components.freeathome as freeathome

REQUIREMENTS = ['slixmpp==1.4.2']

_LOGGER = logging.getLogger(__name__)


# 'switch' will receive discovery_info={'optional': 'arguments'}
# as passed in above. 'light' will receive discovery_info=None
async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """ switch/light specific code."""

    _LOGGER.info('FreeAtHome setup light')

    fah = hass.data[freeathome.DATA_MFH]

    devices = fah.get_devices('light')

    for device, device_object in devices.items():
        async_add_devices([FreeAtHomeLight(device_object)])


class FreeAtHomeLight(Light):
    """ Free@home light """
    light_device = None
    _name = ''
    _state = None
    _brightness = None
    _light_type = None

    def __init__(self, device):
        self.light_device = device
        self._name = self.light_device.name
        self._state = self.light_device.state
        self._light_type = self.light_device.light_type
        if self.light_device.brightness is not None:
            self._brightness = int(float(self.light_device.brightness) * 2.55)
        else:
            self._brightness = None

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return the ID """
        return self.light_device.device_id

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def supported_features(self):
        """Flag supported features."""
        if self._light_type == 'dimmer':
            return SUPPORT_BRIGHTNESS
        return 0

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def brightness(self):
        """Brightness of this light between 0..255."""
        return self._brightness

    async def async_added_to_hass(self):
        """Register callback to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_update_ha_state(True)

        self.light_device.register_device_updated_cb(after_update_callback)

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on.
        """
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            self.light_device.set_brightness(int(self._brightness / 2.55))

        await self.light_device.turn_on()
        self._state = True

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        await self.light_device.turn_off()
        self._state = False

    async def async_update(self):
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self.light_device.is_on()
        if self.light_device.brightness is not None:
            self._brightness = int(float(self.light_device.get_brightness()) * 2.55)
