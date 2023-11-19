''' Main Home Assistant interface Free@Home '''
import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import event
from homeassistant.helpers.discovery import load_platform
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT
import homeassistant.helpers.config_validation as cv

from datetime import datetime

from .const import DOMAIN, CONF_USE_ROOM_NAMES, DEFAULT_USE_ROOM_NAMES, CONF_SWITCH_AS_X, DEFAULT_SWITCH_AS_X, BACKWARD_COMPATIBILE_SWITCH_AS_X

PLATFORMS = [
        "binary_sensor",
        "climate",
        "cover",
        "light",
        "lock",
        "scene",
        "sensor",
        "switch"
        ]

SERVICE_DUMP = "dump"
SERVICE_MONITOR = "monitor"

# Validation of the user's configuration
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_USERNAME, default='admin'): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_USE_ROOM_NAMES,
                     default=DEFAULT_USE_ROOM_NAMES): cv.boolean,
        vol.Optional(CONF_SWITCH_AS_X,
                     default=DEFAULT_SWITCH_AS_X): cv.boolean,
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
    try:
        sysap.switch_as_x = entry.data[CONF_SWITCH_AS_X]
    except KeyError:
        _LOGGER.warning("No switch_as_x option found in saved config, consider adding it")
        sysap.switch_as_x = BACKWARD_COMPATIBILE_SWITCH_AS_X

    hass.data[DOMAIN][entry.entry_id] = sysap

    await sysap.connect()
    await sysap.wait_for_connection()
    await sysap.find_devices()

    for component in PLATFORMS:
        hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, component)
                )

    async def async_dump_service(call):
        """Handle dump service calls."""
        for sysap in hass.data[DOMAIN].values():
            host = sysap.host
            now_formatted = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
            filename = f"freeathome_dump_{host}_{now_formatted}.xml"
            with open(hass.config.path(filename), "wt") as f:
                xml = await sysap.get_raw_config(pretty=True)
                f.write(xml)

            _LOGGER.info("Dumped devices for host %s to %s", host, filename)

        return True

    hass.services.async_register(
            DOMAIN,
            SERVICE_DUMP,
            async_dump_service,
            )

    async def async_monitor_service(call):
        """Handle monitor service calls."""
        for sysap in hass.data[DOMAIN].values():
            host = sysap.host
            now_formatted = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
            filename = f"freeathome_monitor_{host}_{now_formatted}.xml"
            f = open(hass.config.path(filename), "wt")

            _LOGGER.info("Start monitoring for device updates at host %s", host)

            @callback
            def collect_msg(msg):
                try:
                    f.write(msg)
                    f.write("\n")
                    f.flush()
                except IOError:
                    _LOGGER.warning("Error while writing to file")

            sysap.add_update_handler(collect_msg)

            async def finish_dump(_):
                """Stop monitoring and write dump to file"""
                sysap.clear_update_handlers()
                f.close()
                _LOGGER.info("Finished monitoring for device updates at host %s, dumped to %s", host, filename)

            event.async_call_later(hass, call.data["duration"], finish_dump)

    hass.services.async_register(
            DOMAIN,
            SERVICE_MONITOR,
            async_monitor_service,
            schema=vol.Schema(
                {
                    vol.Optional("duration", default=5): int,
                }
            ),
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
