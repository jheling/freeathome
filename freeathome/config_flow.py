"""Config flow for freeathome."""
import logging

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD

from .const import DOMAIN, CONF_USE_ROOM_NAMES  # pylint:disable=unused-import
from .pfreeathome import FreeAtHomeSysApp

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=5222): int,
    vol.Required(CONF_USERNAME, default='admin'): str,
    vol.Optional(CONF_PASSWORD): str,
    vol.Optional(CONF_USE_ROOM_NAMES, default=False): bool,
})


async def validate_input(hass: core.HomeAssistant, data: dict):
    """Validate the user input allows us to connect."""
    sysap = FreeAtHomeSysApp(
            data[CONF_HOST],
            data[CONF_PORT],
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
    )

    # Only try to connect once
    sysap.reconnect = False
    await sysap.connect()

    result = await sysap.wait_for_connection()
    if not result:
        raise CannotConnect

    await sysap.disconnect()

    return {"title": data[CONF_HOST]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for freeathome."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


    async def async_step_import(self, import_config):
        """Import config entry from YAML."""
        return await self.async_step_user(import_config)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
