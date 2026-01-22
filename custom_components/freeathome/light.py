""" Support for Free@Home lights dimmers """
import logging
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_RGB_COLOR, ColorMode, LightEntity)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# 'switch' will receive discovery_info={'optional': 'arguments'}
# as passed in above. 'light' will receive discovery_info=None
async def async_setup_entry(hass, config_entry, async_add_devices, discovery_info=None):
    """ switch/light specific code."""

    _LOGGER.info('FreeAtHome setup light')

    sysap = hass.data[DOMAIN][config_entry.entry_id]

    devices = sysap.get_devices('light')

    for device_object in devices:
        async_add_devices([FreeAtHomeLight(device_object)])


class FreeAtHomeLight(LightEntity):
    """ Free@home light """
    light_device = None
    _name = ''
    _state = None
    _brightness = None
    _is_dimmer = None
    _is_rgb = None
    _is_color_temp = None
    _color_temp_kelvin = None
    _max_color_temp_kelvin = None
    _min_color_temp_kelvin = None
    _rgb_color = None

    def __init__(self, device):
        self.light_device = device
        self._name = self.light_device.name
        self._state = self.light_device.state
        
        self._is_dimmer = self.light_device.is_dimmer()
        if self.light_device.brightness is not None:
            self._brightness = int(float(self.light_device.brightness) * 2.55)
        else:
            self._brightness = None

        self._is_color_temp = self.light_device.is_color_temp()
        if self.light_device.color_temp is not None:
            self._color_temp_kelvin =  self.light_device.get_color_temp()
            self._max_color_temp_kelvin = self.light_device.max_color_temp
            self._min_color_temp_kelvin = self.light_device.min_color_temp
        else:
            self._color_temp_kelvin = None
            self._max_color_temp_kelvin = None
            self._min_color_temp_kelvin = None

        self._is_rgb = self.light_device.is_rgb()
        if self.light_device.rgb_color  is not None:
            self._rgb_color = self.light_device.get_rgb_color()
        else:
            self._rgb_color = None

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def device_info(self):
        """Return device id."""
        return self.light_device.device_info

    @property
    def unique_id(self):
        """Return the ID """
        return self.light_device.serialnumber + '/' + self.light_device.channel_id

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def color_mode(self) -> str | None:
        """Return the color mode of the light."""   
        if self._is_rgb:
            return ColorMode.RGB            
        if self._is_color_temp:
            return ColorMode.COLOR_TEMP
        if self._is_dimmer:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF
    
    @property
    def supported_color_modes(self) -> set[str] | None:
        """Flag supported color modes."""
        if self._is_rgb:
            return {ColorMode.RGB}            
        if self._is_color_temp:
            return {ColorMode.COLOR_TEMP}                
        if self._is_dimmer:
            return {ColorMode.BRIGHTNESS}
        return {ColorMode.ONOFF}    

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def brightness(self):
        """Brightness of this light between 0..255."""
        return self._brightness
    
    @property
    def color_temp_kelvin(self) -> int | None:
        return self._color_temp_kelvin

    @property
    def max_color_temp_kelvin(self) -> int | None:
        return self._max_color_temp_kelvin
    
    @property
    def min_color_temp_kelvin(self) -> int | None:
        return self._min_color_temp_kelvin
    
    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return self._rgb_color

    async def async_added_to_hass(self):
        """Register callback to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_update_ha_state(True)

        self.light_device.register_device_updated_cb(after_update_callback)

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on.
        """
        if ATTR_COLOR_TEMP in kwargs:            
            self._color_temp_kelvin = kwargs[ATTR_COLOR_TEMP]
            self.light_device.set_color_temp(self._color_temp_kelvin)

        if ATTR_RGB_COLOR in kwargs:
            self._rgb_color = kwargs[ATTR_RGB_COLOR]    
            self.light_device.set_rgb_color(int( self._rgb_color[0]), int( self._rgb_color[1]), int( self._rgb_color[2]))

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

        if self.light_device.color_temp is not None:
            self._color_temp_kelvin = self.light_device.get_color_temp()

        if self.light_device.rgb_color is not None:        
            self._rgb_color = self.light_device.get_rgb_color()
