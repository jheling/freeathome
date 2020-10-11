''' Support for Free@Home Sensor devices like temperature sensors, lux sensors '''
import logging

from homeassistant.const import (
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_TEMPERATURE,
    SPEED_KILOMETERS_PER_HOUR,
    TEMP_CELSIUS,
    )

from homeassistant.helpers.entity import Entity

from .const import DOMAIN

from .const import DOMAIN

SENSOR_TYPES = {
    "temperature": [
        "Temperature",
        TEMP_CELSIUS,
        "mdi:thermometer",
        DEVICE_CLASS_TEMPERATURE,
    ],
    "windstrength": [
        "Wind Strength",
        SPEED_KILOMETERS_PER_HOUR,
        "mdi:weather-windy",
        None,
    ],
    "rain": [
        "Rain",
        None,
        "mdi:weather-rainy",
        None],
    "lux": [
        "Illumination",
        "lux",
        None,
        DEVICE_CLASS_ILLUMINANCE],
}

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_devices, discovery_info=None):
    """ setup """

    _LOGGER.info('FreeAtHome setup sensor')

    fah = hass.data[DOMAIN][config_entry.entry_id]

    devices = fah.get_devices('sensor')

    for device, device_object in devices.items():
        async_add_devices([FreeAtHomeSensor(device_object)])

class FreeAtHomeSensor(Entity):
    ''' Interface to the weather sensor devices of Free@Home '''
    _name = ''
    sensor_device = None
    _state = None

    def __init__(self, device):
        self.sensor_device = device
        self.type  = self.sensor_device.type
        self._name = self.sensor_device.name
        self._state = self.sensor_device.state
        self._device_class = SENSOR_TYPES[self.type][3]
        self._icon = SENSOR_TYPES[self.type][2]
        self._unit_of_measurement = SENSOR_TYPES[self.type][1]        

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def device_info(self):
        """Return device id."""
        return self.sensor_device.device_info

    @property
    def unique_id(self):
        """Return the ID """
        return self.sensor_device.serialnumber + '/' + self.sensor_device.channel_id

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def state(self):
        """Return the state of the device."""
        if self._unit_of_measurement == SPEED_KILOMETERS_PER_HOUR:
            return ("%.2f" % (float(self._state) * 3.6))
        else:    
            return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    async def async_added_to_hass(self):
        """Register callback to update hass after device was changed."""
        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_update_ha_state(True)
        self.sensor_device.register_device_updated_cb(after_update_callback)

    async def async_update(self):
        """Retrieve latest state."""
        self._state = self.sensor_device.state
