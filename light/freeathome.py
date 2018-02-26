import asyncio
import custom_components.freeathome as freeathome
import logging

REQUIREMENTS = ['slixmpp==1.3.0']

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.light import Light

# 'switch' will receive discovery_info={'optional': 'arguments'} 
# as passed in above. 'light' will receive discovery_info=None
@asyncio.coroutine
def async_setup_platform(hass, config, add_devices, discovery_info=None):
    """Your switch/light specific code."""
    import custom_components.pfreeathome

    _LOGGER.info('free at home setup light') 

    fah = hass.data[freeathome.DATA_MFH]

    # wait for the roster has completed
    yield from asyncio.sleep(2)
    
    devices = yield from fah.get_devices()

    for device, attributes in devices.items(): 
     
        add_devices([FreeAtHomeLight(fah, device, attributes['name'],attributes['state'])])
     
class FreeAtHomeLight(Light):

    def __init__(self, sysap, device, name,state):
        self._sysap = sysap
        self._device = device
        self._name = name
        self._state = state

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @asyncio.coroutine 
    def async_turn_on(self, **kwargs):
        """Instruct the light to turn on.
        """
        _LOGGER.info("%s turn on", self._device)
        yield from self._sysap.turn_on(self._device)
        self._state = True 

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        _LOGGER.info("%s turn off",self._device)
        yield from self._sysap.turn_off(self._device)
        self._state = False

    @asyncio.coroutine
    def async_update(self):
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        yield from self._sysap.update(self._device)
        self._state = self._sysap.is_on(self._device)        

   
