""" Support for Free@Home scenes. """
import logging
from homeassistant.components.scene import Scene
import custom_components.freeathome as freeathome

REQUIREMENTS = ['slixmpp==1.4.2']

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """ scene specific code """

    _LOGGER.info('FreeAtHome setup scenes')

    fah = hass.data[freeathome.DATA_MFH]

    devices = fah.get_devices('scene')

    for device, device_object in devices.items():
        async_add_devices([FreeAtHomeScene(device_object)])


class FreeAtHomeScene(Scene):
    """ Free@home scene """

    _name = ''
    scene_device = None

    def __init__(self, device):
        self.scene_device = device
        self._name = self.scene_device.name

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

    async def async_added_to_hass(self):
        """Register callback to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_update_ha_state(True)

        self.scene_device.register_device_updated_cb(after_update_callback)

    async def async_activate(self):
        """Activate scene. Try to get entities into requested state."""
        await self.scene_device.activate()
