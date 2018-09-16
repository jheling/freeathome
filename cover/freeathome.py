"""

Support for Free @ Home cover - blinds , shutters.


"""

import asyncio
import custom_components.freeathome as freeathome
import logging

REQUIREMENTS = ['slixmpp==1.3.0']

from homeassistant.components.cover import (
    CoverDevice, ENTITY_ID_FORMAT, ATTR_POSITION,
    SUPPORT_CLOSE, SUPPORT_OPEN, SUPPORT_SET_POSITION,SUPPORT_STOP
    )


_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config, add_devices, discovery_info=None):
    """Your switch/light specific code."""
    import custom_components.pfreeathome

    _LOGGER.info('FreeAtHome setup cover') 

    fah = hass.data[freeathome.DATA_MFH]
    
    devices = fah.get_devices('cover')

    for device, attributes in devices.items():      
        add_devices([FreeAtHomeCover(fah, device, attributes['name'],attributes['state'])])                     

class FreeAtHomeCover(CoverDevice):

    def __init__(self, sysap, device, name,state):
        self._sysap = sysap
        self._device = device
        self._name = name
        self._state = state

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = SUPPORT_OPEN | SUPPORT_CLOSE | \
            SUPPORT_SET_POSITION | SUPPORT_STOP
        return supported_features        
        
    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return the ID """
        return self._device    

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._sysap.is_cover_closed(self._device)         

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self._sysap.is_closing(self._device)
        
    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return self._sysap.is_opening(self._device)        
        
    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._sysap.get_cover_position(self._device)        
        
    @asyncio.coroutine     
    def async_close_cover(self, **kwargs):
        """Open the cover."""
        yield from self._sysap.close(self._device)
        
    @asyncio.coroutine 
    def async_open_cover(self, **kwargs):
        """Close the cover."""
        yield from self._sysap.open(self._device)
        
    @asyncio.coroutine 
    def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        yield from self._sysap.stop(self._device)
                
    @asyncio.coroutine
    def async_update(self):    
        """Fetch new state data for this cover.

        This is the only method that should fetch new data for Home Assistant.
        """
        yield from self._sysap.update(self._device)
        self._state = self._sysap.is_cover_closed(self._device)
    
    @asyncio.coroutine 
    def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)
        yield from self._sysap.set_cover_position(self._device, position)
    