""" Support for Free@Home Binary devices like sensors, movement detectors """
import asyncio
import logging
from homeassistant.components.binary_sensor import (BinarySensorEntity, BinarySensorDeviceClass)
from .const import DOMAIN
from .fah_event import create_event_data

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_devices, discovery_info=None):
    """ setup """

    _LOGGER.info('FreeAtHome setup binary sensor')

    fah = hass.data[DOMAIN][config_entry.entry_id]

    devices = fah.get_devices('binary_sensor')

    for device_object in devices:
        async_add_devices([FreeAtHomeBinarySensor(device_object,hass)])


class FreeAtHomeBinarySensor(BinarySensorEntity):
    """ Interface to the binary devices of Free@Home """
    _name = ''
    binary_device = None
    _state = None
    _hass = None
    _reset_task = None

    def __init__(self, device, hass):
        self.binary_device = device
        self._name = self.binary_device.name
        if self.binary_device.is_door_call_sensor():
            self.binary_device.state = '0'
        self._state = (self.binary_device.state == '1')
        self._hass = hass
        self._reset_task = None

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def device_info(self):
        """Return device id."""
        return self.binary_device.device_info

    @property
    def unique_id(self):
        """Return the ID """
        return self.binary_device.unique_id

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state
    
    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of the binary sensor."""

        if self.binary_device.is_fire_sensor():
            return BinarySensorDeviceClass.SMOKE 
        
        if self.binary_device.is_co_sensor():
            return BinarySensorDeviceClass.CO

        if self.binary_device.is_door_call_sensor():
            return BinarySensorDeviceClass.OCCUPANCY

        return None

    @property
    def icon(self) -> str | None:
        """Return the icon of the binary sensor."""
        if self.binary_device.is_door_call_sensor():
            return "mdi:doorbell"
        return None

    @property
    def extra_state_attributes(self):
        """Return specific state attributes."""
        attributes = {}
        if self.binary_device.window_position == '0':
            attributes["window_position"] = "closed"
        elif self.binary_device.window_position == '33':
            attributes["window_position"] = "tilted"
        elif self.binary_device.window_position == '100':
            attributes["window_position"] = "open"

        return attributes

    async def _async_auto_reset(self):
        """Reset door call sensor state after a momentary pulse."""
        try:
            await asyncio.sleep(2)
            if self._state:
                self._state = False
                self.binary_device.state = '0'
                self.async_write_ha_state()
        except asyncio.CancelledError:
            pass

    async def async_added_to_hass(self):
        """Register callback to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            if self.binary_device.is_door_call_sensor() and self._state and self.binary_device.state == '1':
                self._state = False
                self.async_write_ha_state()
            await self.async_update_ha_state(True)
            if self.binary_device.is_door_call_sensor() and self._state:
                if self._reset_task and not self._reset_task.done():
                    self._reset_task.cancel()
                self._reset_task = self._hass.async_create_task(self._async_auto_reset())

        async def datapoint_updated_callback(device, event):
            """Fire an event containing the decoded datapoint command."""
            eventdata = create_event_data(
                self._name, device.serialnumber, self.unique_id, event)
            self._hass.bus.async_fire("freeathome_event", eventdata)

        self.binary_device.register_device_updated_cb(after_update_callback)
        self.binary_device.register_datapoint_updated_cb(datapoint_updated_callback)
        self.async_on_remove(
            lambda: self.binary_device.unregister_device_cb(
                after_update_callback))
        self.async_on_remove(
            lambda: self.binary_device.unregister_datapoint_updated_cb(
                datapoint_updated_callback))

    async def async_will_remove_from_hass(self):
        """Cancel pending tasks when entity is removed."""
        if self._reset_task and not self._reset_task.done():
            self._reset_task.cancel()

    async def async_update(self):
        """Retrieve latest state."""

        self._state = (self.binary_device.state == '1')
        _LOGGER.info('update sensor')
