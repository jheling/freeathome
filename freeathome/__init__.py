''' Main Home Assistant interface Free@Home '''
import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import load_platform
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_USE_ROOM_NAMES

PLATFORMS = [
        "binary_sensor",
        "climate",
        "cover",
        "light",
        "lock",
        "scene",
        "sensor",
        ]


DEFAULT_USE_ROOM_NAMES = False

# Validation of the user's configuration
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_USERNAME, default='admin'): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_USE_ROOM_NAMES,
                     default=DEFAULT_USE_ROOM_NAMES): cv.boolean,
    })
}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, base_config: dict):
    """ Setup of the Free@Home interface for Home Assistant ."""
    hass.data.setdefault(DOMAIN, {})
    if DOMAIN not in base_config or hass.config_entries.async_entries(DOMAIN):
        return True

    conf = base_config[DOMAIN]

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=conf,
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .fah import pfreeathome

    sysap = pfreeathome.FreeAtHomeSysApp(
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD])

    sysap.use_room_names = entry.data[CONF_USE_ROOM_NAMES]
    hass.data[DOMAIN][entry.entry_id] = sysap

    await sysap.connect()
    await sysap.wait_for_connection()
    await sysap.find_devices()

    for component in PLATFORMS:
        hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, component)
                )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    sysap = hass.data[DOMAIN][entry.entry_id]
    await sysap.disconnect()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
