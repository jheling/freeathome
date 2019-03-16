""" Support for Free@Home thermostats """

import logging

import custom_components.freeathome as freeathome
from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (STATE_AUTO, STATE_ECO,
                                                    SUPPORT_ON_OFF,
                                                    SUPPORT_OPERATION_MODE,
                                                    SUPPORT_TARGET_TEMPERATURE)
from homeassistant.const import (ATTR_TEMPERATURE, DEVICE_CLASS_TEMPERATURE,
                                 STATE_OFF, STATE_ON, TEMP_CELSIUS)

REQUIREMENTS = ['slixmpp==1.4.2']

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_devices, discovery_info=None):
    """ thermostat specific code."""
    _LOGGER.info('FreeAtHome setup thermostat')

    fah = hass.data[freeathome.DATA_MFH]

    devices = fah.get_devices('thermostat')

    for device, device_object in devices.items():
        add_devices([FreeAtHomeThermostat(device_object)])


# ch0, odp0008 = 1 == on
# ch0, odp0006 = 19 == target temp

# ch0, odp0008 = 0 == off
# ch0, odp0006 = 7 == ??????????????????????

# ch0, odp0009 = 68 == eco mode on
# ch0, odp0006 = 16 == target temp in eco mode (param pm0000 == 3)

# ch0, odp0009 = 65 = eco mode off
# ch0, odp0006 = 19 = target temp

# pm0000 = temperature reduction in ECO mode
# pm0001 = temperature correction
# pm0002 = target temperature
# pm0003 = delay
# pm0004 = 60 ?
# pm0005 = 
# pm0006 = 0 ?
# pm0007 = 
# pm0008 = 14 ?
# pm0009 = -14 ?
# pm000a = 1 ?
# pm000b = led backlight% (day?)
# pm000c = led backlight% (night?)



class FreeAtHomeThermostat(ClimateDevice):
    ''' Free@home thermostat '''
    thermostat_device = None
    _name = ''
    _current_operation = None

    def __init__(self, device):
        self.thermostat_device = device
        self._name = self.thermostat_device.name
        self._state = self.thermostat_device.state

    @property
    def name(self):
        """Return the display name of this thermostat."""
        return self._name

    @property
    def unique_id(self):
        """Return the ID """
        return self.thermostat_device.device_id

    @property
    def should_poll(self):
        """Thermostat should be polled"""
        return True

    @property
    def current_temperature(self):
        """Return the current temperature."""
        if self.current_operation == STATE_OFF:
            return None
        return float(self.thermostat_device.current_temperature)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return float(self.thermostat_device.target_temperature)

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE | SUPPORT_ON_OFF

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return [STATE_ECO, STATE_AUTO]

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self._current_operation

    @property
    def icon(self):
        return 'mdi:thermometer-lines'

    async def async_turn_off(self):
        """Turn device off."""
        await self.thermostat_device.turn_off()
        self._current_operation = STATE_OFF

    async def async_turn_on(self):
        """Turn device on."""
        await self.thermostat_device.turn_on()
        self._current_operation = STATE_ON

    async def async_set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        if operation_mode == STATE_ECO:
            await self.thermostat_device.eco_mode()

        if operation_mode == STATE_AUTO:
            await self.thermostat_device.turn_on()

        self._current_operation = operation_mode

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        await self.thermostat_device.set_target_temperature(temperature)

    async def async_update(self):
        if self.thermostat_device.state:
            self.current_operation = STATE_ON
        elif self.thermostat_device.ecomode:
            self.current_operation = STATE_ECO
        else:
            self.current_operation = STATE_OFF
