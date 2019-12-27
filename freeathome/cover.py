""" Support for Free@Home cover - blinds , shutters. """
import logging
from homeassistant.components.cover import (
    CoverDevice, ATTR_POSITION,
    SUPPORT_CLOSE, SUPPORT_OPEN, SUPPORT_SET_POSITION, SUPPORT_STOP
)
import custom_components.freeathome as freeathome

REQUIREMENTS = ['slixmpp==1.4.2']

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """ cover specific code."""

    _LOGGER.info('FreeAtHome setup cover')

    fah = hass.data[freeathome.DATA_MFH]

    devices = fah.get_devices('cover')

    for device, device_object in devices.items():
        async_add_devices([FreeAtHomeCover(device_object)])


class FreeAtHomeCover(CoverDevice):
    """interface cover/blinds  """
    cover_device = None
    _name = ''
    _state = None

    def __init__(self, device):
        self.cover_device = device

        self._name = self.cover_device.name
        self._state = self.cover_device.state

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION | SUPPORT_STOP
        return supported_features

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return the ID """
        return self.cover_device.device_id

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self.cover_device.is_cover_closed()

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self.cover_device.is_cover_closing()

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return self.cover_device.is_cover_opening()

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self.cover_device.get_cover_position()

    async def async_added_to_hass(self):
        """Register callback to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_update_ha_state(True)

        self.cover_device.register_device_updated_cb(after_update_callback)

    async def async_close_cover(self, **kwargs):
        """Open the cover."""
        await self.cover_device.close_cover()

    async def async_open_cover(self, **kwargs):
        """Close the cover."""
        await self.cover_device.open_cover()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self.cover_device.stop_cover()

    async def async_update(self):
        """Fetch new state data for this cover.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self.cover_device.is_cover_closed()

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)

        await self.cover_device.set_cover_position(position)
