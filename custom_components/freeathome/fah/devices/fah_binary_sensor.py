import asyncio
import logging
import time

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

# free@home cyclically re-sends output datapoints with their last value
# (observed period: exactly 840 s). These repetitions are keep-alives, not new
# events, but update_datapoint() cannot tell them apart and sets state to '1'
# again. If the sensor has been reset to '0' in the meantime, the repetition
# produces a ghost motion event. Measured on six motion detectors over 7 days:
# 37 % of all triggers were such repetitions (period 840.0 s, spread below
# 0.6 s across all six devices); real motion never happened to land on this
# grid. A repetition is only discarded when it carries the SAME value as the
# previous telegram of the SAME datapoint and arrives CYCLIC_PERIOD after it.
CYCLIC_PERIOD = 840.0
CYCLIC_TOLERANCE = 2.0


class FahBinarySensor(FahDevice):
    """Free@Home binary object """
    state = None
    window_position = None
    # Created lazily per instance on the first telegram (deliberately NOT a
    # dict literal here: that would be a class attribute shared by all sensors).
    _cyclic_last = None

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


    def _is_cyclic_repeat(self, dp, value):
        """True if dp repeats its previous identical value exactly CYCLIC_PERIOD later."""
        # Never filter safety-critical datapoints.
        for pid in (PID_FIRE_ALARM_ACTIVE, PID_CO_ALARM_ACTIVE):
            if self._datapoints.get(pid) == dp:
                return False

        if self._cyclic_last is None:
            self._cyclic_last = {}

        now = time.monotonic()
        previous = self._cyclic_last.get(dp)
        self._cyclic_last[dp] = (now, value)

        if previous is None:
            return False
        last_time, last_value = previous
        # A changed value is always a real event, never a repetition.
        if value != last_value:
            return False
        return abs((now - last_time) - CYCLIC_PERIOD) <= CYCLIC_TOLERANCE

    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_WINDOW_DOOR_POSITION) == dp:
            self.window_position = value
            LOG.info("binary sensor %s (%s) dp %s state %s", self.name, self.lookup_key, dp, value)
            return

        if self._is_cyclic_repeat(dp, value):
            LOG.debug("binary sensor %s (%s) dp %s: cyclic repeat of value %s ignored",
                      self.name, self.lookup_key, dp, value)
            return

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
