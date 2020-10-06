""" Support for Free@Home cover forced position """
import logging
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STATE_FORCED_POSITION_OFF = 0
COMMAND_FORCED_POSITION_TURN_OFF = 1
STATE_FORCED_POSITION_UP = 2
STATE_FORCED_POSITION_DOWN = 3


# 'switch' will receive discovery_info={'optional': 'arguments'}
# as passed in above. 'light' will receive discovery_info=None
async def async_setup_entry(hass, config_entry, async_add_devices, discovery_info=None):
    """ switch/light specific code."""

    _LOGGER.info('FreeAtHome setup switch')

    fah = hass.data[DOMAIN][config_entry.entry_id]

    cover_devices = fah.get_devices('cover')

    for device, device_object in cover_devices.items():
        async_add_devices([
            FreeAtHomeCoverForcedPositionSwitch(device_object, STATE_FORCED_POSITION_UP, "up"),
            FreeAtHomeCoverForcedPositionSwitch(device_object, STATE_FORCED_POSITION_DOWN, "down"),
            ])


class FreeAtHomeCoverForcedPositionSwitch(SwitchEntity):
    """ Free@home switch for forced cover position """
    cover_device = None
    _forced_position = None
    _name = ''
    _name_suffix = ''
    _state = None

    def __init__(self, cover_device, forced_position, name_suffix):
        self.cover_device = cover_device
        self._forced_position = forced_position
        self._name = self.cover_device.name
        self._name_suffix = name_suffix
        self._state = self.cover_device.forced_position

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name + " force " + self._name_suffix

    @property
    def unique_id(self):
        """Return the ID """
        return self.cover_device.device_id + "_" + self._name_suffix

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def supported_features(self):
        """Flag supported features."""
        return 0

    @property
    def is_on(self):
        """Return true if correct forced position is set."""
        return self._state == self._forced_position

    async def async_added_to_hass(self):
        """Register callback to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_update_ha_state(True)

        self.cover_device.register_device_updated_cb(after_update_callback)

    async def async_turn_on(self, **kwargs):
        """Instruct the cover to force stay open or closed."""
        await self.cover_device.set_forced_cover_position(self._forced_position)
        self._state = True

    async def async_turn_off(self, **kwargs):
        """Instruct the cover to return to previous position."""
        await self.cover_device.set_forced_cover_position(COMMAND_FORCED_POSITION_TURN_OFF)
        self._state = False

    async def async_update(self):
        """Fetch new state data for this switch.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self.cover_device.get_forced_cover_position()
