''' Main Home Assistant interface Free@Home '''
import  logging
import voluptuous as vol
from homeassistant.helpers.discovery import load_platform
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT
import homeassistant.helpers.config_validation as cv

REQUIREMENTS =  ['slixmpp==1.4.2']

DOMAIN = 'freeathome'

DATA_MFH = 'FAH'
CONF_USE_ROOM_NAMES = 'use_room_names'
DEFAULT_USE_ROOM_NAMES = False

# Validation of the user's configuration
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=5222): cv.port,
        vol.Optional(CONF_USERNAME, default='admin'): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_USE_ROOM_NAMES,
                     default=DEFAULT_USE_ROOM_NAMES): cv.boolean,
    })
}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, base_config):
    """ Setup of the Free@Home interface for Home Assistant ."""
    import custom_components.pfreeathome as pfreeathome

    config = base_config.get(DOMAIN)

    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    sysap = pfreeathome.FreeAtHomeSysApp(host, port, username, password)
    sysap.use_room_names = config.get(CONF_USE_ROOM_NAMES)
    sysap.connect()

    hass.data[DATA_MFH] = sysap

    resp = await sysap.wait_for_connection()

    if resp:
        await sysap.find_devices()

        load_platform(hass, 'light', DOMAIN, {}, config)
        load_platform(hass, 'scene', DOMAIN, {}, config)
        load_platform(hass, 'cover', DOMAIN, {}, config)
        load_platform(hass, 'binary_sensor', DOMAIN, {}, config)

        return True

    return False
