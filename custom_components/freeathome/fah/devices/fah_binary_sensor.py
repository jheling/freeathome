import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
        FUNCTION_IDS_BINARY_SENSOR,
        FUNCTION_IDS_WEATHER_STATION,
        FUNCTION_IDS_DOORBELL_SENSOR,
        PID_SWITCH_ON_OFF,
        PID_TIMED_START_STOP,
        PID_FORCE_POSITION,
        PID_SCENE_CONTROL,
        PID_RELATIVE_SET_VALUE,
        PID_MOVE_UP_DOWN,
        PID_ADJUST_UP_DOWN,
        PID_WIND_ALARM,
        PID_FROST_ALARM,
        PID_RAIN_ALARM,
        PID_BRIGHTNESS_ALARM,
        PID_FORCE_POSITION_BLIND,
        PID_WINDOW_DOOR,
        PID_WINDOW_DOOR_POSITION,
        PID_SWITCHOVER_HEATING_COOLING,
        PID_MOVEMENT_UNDER_CONSIDERATION_OF_BRIGHTNESS,
        PID_PRESENCE,
        PID_FIRE_ALARM_ACTIVE,
        PID_CO_ALARM_ACTIVE,
        )

LOG = logging.getLogger(__name__)

class FahBinarySensor(FahDevice):
    """Free@Home binary object """
    state = None
    window_position = None

    def pairing_ids(function_id=None):
        if function_id in FUNCTION_IDS_BINARY_SENSOR:
            return {
                    "inputs": [],
                    "outputs": [
                        PID_SWITCH_ON_OFF,
                        # Add timed start/stop, even though in tests it only ever showed value '1'
                        PID_TIMED_START_STOP,
                        PID_FORCE_POSITION,
                        # Keep scene control here, although in tests it never showed up
                        #PID_SCENE_CONTROL,
                        PID_RELATIVE_SET_VALUE,
                        PID_MOVE_UP_DOWN,
                        PID_ADJUST_UP_DOWN,
                        PID_WIND_ALARM,
                        PID_FROST_ALARM,
                        PID_RAIN_ALARM,
                        PID_BRIGHTNESS_ALARM,
                        PID_FORCE_POSITION_BLIND,
                        PID_WINDOW_DOOR,
                        PID_WINDOW_DOOR_POSITION,
                        PID_SWITCHOVER_HEATING_COOLING,
                        # Keep movement detector here, although in tests it only ever showed value '1'
                        PID_MOVEMENT_UNDER_CONSIDERATION_OF_BRIGHTNESS,
                        PID_PRESENCE,
                        PID_FIRE_ALARM_ACTIVE,
                        PID_CO_ALARM_ACTIVE,
                        ]
                    }
        elif function_id in FUNCTION_IDS_WEATHER_STATION:
            return {
                    "inputs": [],
                    "outputs": [
                        PID_WIND_ALARM,
                        PID_FROST_ALARM,
                        PID_BRIGHTNESS_ALARM,
                        ]

                    }
        elif function_id in FUNCTION_IDS_DOORBELL_SENSOR:
            return {
                    "inputs": [],
                    "outputs": [
                        PID_TIMED_START_STOP,                        
                        ]
            }


    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_WINDOW_DOOR_POSITION) == dp:
            self.window_position = value
        else:
            self.state = '0' if value == '0' else '1'
        LOG.info("binary sensor %s (%s) dp %s state %s", self.name, self.lookup_key, dp, value)

    def get_icon(self):
        if self._function_id in FUNCTION_IDS_DOORBELL_SENSOR: 
            return "mdi:doorbell"
        else:
            return None

    def is_fire_sensor(self):
        """Return true if device is a fire sensor"""
        return PID_FIRE_ALARM_ACTIVE in self._datapoints

    def is_co_sensor(self):
        """Return true if device is a co sensor"""
        return PID_CO_ALARM_ACTIVE in self._datapoints

    def update_parameter(self, param, value):
        LOG.debug("Not yet implemented")
