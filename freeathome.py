import  logging
import asyncio
from homeassistant.helpers.discovery import load_platform
from homeassistant.components.light import ATTR_BRIGHTNESS, Light, PLATFORM_SCHEMA
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD,CONF_PORT

REQUIREMENTS = ['slixmpp==1.3.0']

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

@asyncio.coroutine
def async_setup(hass, base_config):
    """Your controller/hub specific code."""
    import custom_components.pfreeathome as pfreeathome
    
    config = base_config.get(DOMAIN)

    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    use_room_names = config.get(CONF_USE_ROOM_NAMES)
    
    sysap = pfreeathome.freeathomesysapp(host, port, username, password, use_room_names)
    sysap.connect()
    
    hass.data[DATA_MFH] = sysap
    
    yield from sysap.wait_for_connection()
    
    yield from sysap.find_devices()
        
    #--- snip ---
    load_platform(hass, 'light', DOMAIN)
    load_platform(hass, 'scene', DOMAIN)
    
    return True
