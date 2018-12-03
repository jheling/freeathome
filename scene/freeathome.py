""" Support for Free@Home scenes. """
import logging
from homeassistant.components.scene import Scene
import custom_components.freeathome as freeathome

REQUIREMENTS = ['slixmpp==1.3.0']

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, add_devices, discovery_info=None):
    ''' scene specific code '''
    import custom_components.pfreeathome

    _LOGGER.info('FreeAtHome setup scenes')

    fah = hass.data[freeathome.DATA_MFH]

    devices = fah.get_devices('scene')

    for device, device_object in devices.items():
        add_devices([FreeAtHomeScene(device_object)])

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

    async def async_activate(self):
        """Activate scene. Try to get entities into requested state."""
        await self.scene_device.activate()
