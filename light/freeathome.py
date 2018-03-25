import asyncio
import custom_components.freeathome as freeathome
import logging

REQUIREMENTS = ['slixmpp==1.3.0']

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, Light)

# 'switch' will receive discovery_info={'optional': 'arguments'} 
# as passed in above. 'light' will receive discovery_info=None
@asyncio.coroutine
def async_setup_platform(hass, config, add_devices, discovery_info=None):
    """Your switch/light specific code."""
    import custom_components.pfreeathome

    _LOGGER.info('FreeAtHome setup light') 

    fah = hass.data[freeathome.DATA_MFH]
    
    devices = fah.get_devices('light')

    for device, attributes in devices.items(): 
     
        add_devices([FreeAtHomeLight(fah, device, attributes['name'],attributes['state'],attributes['light_type'],attributes)])
     
class FreeAtHomeLight(Light):

    def __init__(self, sysap, device, name,state,light_type,attributes):
        self._sysap = sysap
        self._device = device
        self._name = name
        self._state = state
        self._light_type = light_type
        if attributes['brightness'] is not None:
            self._brightness = int(attributes['brightness'] * 2.55)
        else:    
            self._brightness = None

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return the ID """
        return self._device
        
    @property
    def supported_features(self):
        """Flag supported features."""
        if self._light_type == 'dimmer':
            return SUPPORT_BRIGHTNESS
        else:
            return 0
    
    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def brightness(self):
        """Brightness of this light between 0..255."""
        return self._brightness
    
    @asyncio.coroutine 
    def async_turn_on(self, **kwargs):
        """Instruct the light to turn on.
        """
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            self._sysap.set_brightness(self._device, int(self._brightness / 2.55) )
        
        yield from self._sysap.turn_on(self._device)
        self._state = True        

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        yield from self._sysap.turn_off(self._device)
        self._state = False

    @asyncio.coroutine
    def async_update(self):
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        yield from self._sysap.update(self._device)
        self._state = self._sysap.is_on(self._device)
        if self._brightness is not None: 
            self._brightness = int(self._sysap.get_brightness(self._device) * 2.55)
   
