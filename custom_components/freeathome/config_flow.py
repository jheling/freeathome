"""Config flow for freeathome."""

import ipaddress
import logging
import socket
from ipaddress import IPv4Address

import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.helpers.service_info import zeroconf
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
)

from .const import (
    CONF_SWITCH_AS_X,
    CONF_USE_ROOM_NAMES,
    DEFAULT_SWITCH_AS_X,
    DEFAULT_USE_ROOM_NAMES,
    DOMAIN,
)  # pylint:disable=unused-import
from .fah.pfreeathome import FreeAtHomeSysApp
from .fah.settings import SettingsFah

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: core.HomeAssistant, data: dict):
    """Validate the user input allows us to connect."""
    sysap = FreeAtHomeSysApp(
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )

    # Only try to connect once
    sysap.reconnect = False
    await sysap.connect()

    result = await sysap.wait_for_connection()
    # Read the reason before disconnecting.
    auth_failed = sysap.authentication_in_error()

    await sysap.disconnect()

    if not result:
        if auth_failed:
            raise InvalidAuth
        raise CannotConnect

    return {"title": data[CONF_HOST]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for freeathome."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize."""
        self.discovered_conf = {}

    """ free@home found thru zeroconf """

    async def async_step_zeroconf(self, discovery_info: zeroconf.ZeroconfServiceInfo):
        """Handle zeroconf discovery."""
        if not isinstance(discovery_info.ip_address, IPv4Address):
            return self.async_abort(reason="not_ipv4address")

        friendly_name = discovery_info.name.split(":", 1)[1].split(".", 1)[0]
        freeathome_host = discovery_info.ip_address.exploded

        settings = SettingsFah(freeathome_host)

        found = await settings.load_json()
        if not found:
            self.async_abort("not_sysap")

        serial_number = settings.get_flag("serialNumber")
        if not serial_number:
            self.async_abort("serialNumber_not_found")

        await self.async_set_unique_id(serial_number)
        self._abort_if_unique_id_configured(updates={CONF_HOST: freeathome_host})

        self.discovered_conf = {
            CONF_NAME: friendly_name,
            CONF_HOST: freeathome_host,
        }

        self.context["title_placeholders"] = self.discovered_conf

        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is None:
            return await self._show_setup_form(user_input, None)

        if self.discovered_conf:
            user_input.update(self.discovered_conf)

        host = user_input[CONF_HOST]
        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]

        # checking the user input
        if check_ip_adress(host):
            ip_adress = host
        else:
            # maybe it is a hostname
            ip_adress = get_host_name_ip(host)
            if ip_adress is None:
                errors[CONF_HOST] = "unknown_host"

        # checking user
        settings = SettingsFah(ip_adress)
        found = await settings.load_json()

        if found:
            jid = settings.get_jid(username)
            if jid is None:
                errors[CONF_USERNAME] = "unknown_user"
        else:
            errors[CONF_HOST] = "no_sysap"
            _LOGGER.info("not a sysap")

        if errors:
            return await self._show_setup_form(user_input, errors)

        """Handle the initial step."""
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                serial_number = settings.get_flag("serialNumber")
                await self.async_set_unique_id(
                    serial_number if serial_number else ip_adress,
                    raise_on_progress=False,
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        if errors:
            return await self._show_setup_form(user_input, errors)
        """
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
        """

    async def async_step_import(self, import_config):
        """Import config entry from YAML."""
        return await self.async_step_user(import_config)

    async def async_step_link(self, user_input):
        """Link a config entry from discovery."""
        return await self.async_step_user(user_input)

    async def async_step_reauth(self, entry_data):
        """Start reauth after the SysAP rejected the stored credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Ask for the credentials again and check them against the SysAP."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors = {}

        if user_input is not None:
            # The host is deliberately not part of this form. A changed host is
            # not an authentication problem and belongs in the reconfigure step.
            data = {**entry.data, **user_input}
            errors = await self._validate_against_sysap(data, entry)

            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data=data,
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_reauth_schema_with_defaults(entry.data),
            errors=errors,
            description_placeholders={CONF_HOST: entry.data[CONF_HOST]},
        )

    async def async_step_reconfigure(self, user_input=None):
        """Reconfigure an existing entry, e.g. after the SysAP changed address."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors = {}

        if user_input is not None:
            # Username and password are not part of this form; they belong in
            # reauth. The stored credentials are what prove that the host given
            # here is reachable and is still the same SysAP.
            data = {**entry.data, **user_input}
            errors = await self._validate_against_sysap(data, entry)

            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data=data,
                    reason="reconfigure_successful",
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_reconfigure_schema_with_defaults(user_input or entry.data),
            errors=errors,
        )

    async def _validate_against_sysap(self, data, entry):
        """Run the checks of the initial setup against a complete data set.

        Returns the errors for the form, empty if everything checks out.
        """
        errors = {}

        host = data[CONF_HOST]
        if check_ip_adress(host):
            ip_adress = host
        else:
            # maybe it is a hostname
            ip_adress = get_host_name_ip(host)
            if ip_adress is None:
                return {CONF_HOST: "unknown_host"}

        settings = SettingsFah(ip_adress)
        found = await settings.load_json()
        if not found:
            _LOGGER.info("not a sysap")
            return {CONF_HOST: "no_sysap"}

        jid = settings.get_jid(data[CONF_USERNAME])
        if jid is None:
            errors[CONF_USERNAME] = "unknown_user"

        serial_number = settings.get_flag("serialNumber")
        new_unique_id = serial_number if serial_number else ip_adress
        if entry.unique_id and new_unique_id != entry.unique_id:
            errors[CONF_HOST] = "other_sysap"

        if errors:
            return errors

        try:
            await validate_input(self.hass, data)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        return errors

    async def _show_setup_form(self, user_input=None, errors=None):
        """Show the setup form to the user."""
        if not user_input:
            user_input = {}

        if self.discovered_conf:
            user_input.update(self.discovered_conf)
            step_id = "link"
            data_schema = _discovery_schema_with_defaults(user_input)
        else:
            step_id = "user"
            data_schema = _user_schema_with_defaults(user_input)

        return self.async_show_form(
            step_id=step_id,
            data_schema=data_schema,
            errors=errors or {},
            description_placeholders=self.discovered_conf or {},
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate the SysAP rejected the credentials."""


def _discovery_schema_with_defaults(discovery_info):
    return vol.Schema(_ordered_shared_schema(discovery_info))


def _user_schema_with_defaults(user_input):
    user_schema = {
        vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
    }
    user_schema.update(_ordered_shared_schema(user_input))

    return vol.Schema(user_schema)


def _reauth_schema_with_defaults(schema_input):
    # No default for the password: it must be entered anew, so a stale
    # stored value can never be written back unnoticed.
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=schema_input.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD): str,
        }
    )


def _reconfigure_schema_with_defaults(schema_input):
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=schema_input.get(CONF_HOST, "")): str,
            vol.Optional(
                CONF_USE_ROOM_NAMES,
                default=schema_input.get(CONF_USE_ROOM_NAMES, DEFAULT_USE_ROOM_NAMES),
            ): bool,
            vol.Optional(
                CONF_SWITCH_AS_X,
                default=schema_input.get(CONF_SWITCH_AS_X, DEFAULT_SWITCH_AS_X),
            ): bool,
        }
    )


def _ordered_shared_schema(schema_input):
    return {
        vol.Required(CONF_USERNAME, default=schema_input.get(CONF_USERNAME, "")): str,
        vol.Required(CONF_PASSWORD, default=schema_input.get(CONF_PASSWORD, "")): str,
        vol.Optional(CONF_USE_ROOM_NAMES, default=DEFAULT_USE_ROOM_NAMES): bool,
        vol.Optional(CONF_SWITCH_AS_X, default=DEFAULT_SWITCH_AS_X): bool,
    }


def check_ip_adress(host):
    try:
        ip = ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def get_host_name_ip(host_name):
    try:
        host_ip = socket.gethostbyname(host_name)
    except:
        return None
