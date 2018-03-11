"""
Support for FreeATHome scenes.


"""
import asyncio
import custom_components.freeathome as freeathome
import logging
from homeassistant.components.scene import Scene

REQUIREMENTS = ['slixmpp==1.3.0']

_LOGGER = logging.getLogger(__name__)

@asyncio.coroutine
def async_setup_platform(hass, config, add_devices, discovery_info=None):
    import custom_components.pfreeathome

    _LOGGER.info('FreeAtHome setup scenes') 

    fah = hass.data[freeathome.DATA_MFH]
   
    devices = fah.get_devices('scene')

    for device, attributes in devices.items(): 
     
        add_devices([FreeAtHomeScene(fah, device, attributes['name'])])

class FreeAtHomeScene(Scene):
    """Representation of a Vera scene entity."""

    def __init__(self, sysap, device, name):
        self._sysap = sysap
        self._device = device
        self._name = name

    @property
    def name(self):
        """Return the name of the scene."""
        return self._name

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def is_on(self):
        """There is no way of detecting if a scene is active (yet)."""
        return False

    @asyncio.coroutine
    def async_activate(self):
        """Activate scene. Try to get entities into requested state."""
        yield from self._sysap.activate(self._device)
    
 