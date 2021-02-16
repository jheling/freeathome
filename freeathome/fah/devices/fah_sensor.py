import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
        FUNCTION_IDS_MOVEMENT_DETECTOR,
        FUNCTION_IDS_WEATHER_STATION,
        PID_MEASURED_BRIGHTNESS,
        PID_OUTDOOR_TEMPERATURE,
        PID_WIND_SPEED,
        PID_RAIN_DETECTION,
        )

LOG = logging.getLogger(__name__)

def sensor_type_from_pairing_ids(datapoints):
    for pairing_id, dp in datapoints.items():
        if dp is None:
            continue

        if pairing_id == PID_MEASURED_BRIGHTNESS:
            return "lux"
        elif pairing_id == PID_RAIN_DETECTION:
            return "rain"
        elif pairing_id == PID_OUTDOOR_TEMPERATURE:
            return "temperature"
        elif pairing_id == PID_WIND_SPEED:
            return "windstrength"


# # TODO: Use FahSensor for weather station sensors
class FahSensor(FahDevice):
    """ Free@Home sensor object """
    state = None

    def pairing_ids(function_id=None):
        if function_id in FUNCTION_IDS_MOVEMENT_DETECTOR:
            return {
                    "inputs": [],
                    "outputs": [
                        PID_MEASURED_BRIGHTNESS,
                        ]
                    }

        elif function_id in FUNCTION_IDS_WEATHER_STATION:
            return {
                    "inputs": [],
                    "outputs": [
                        PID_OUTDOOR_TEMPERATURE,
                        PID_MEASURED_BRIGHTNESS,
                        PID_WIND_SPEED,
                        PID_RAIN_DETECTION,
                        ]
                    }


    def __init__(self, client, device_info, serialnumber, channel_id, name, datapoints={}, device_updated_cb=None):
        # Determine sensor type (e.g. temperature, brightness) from datapoints
        self.type = sensor_type_from_pairing_ids(datapoints)

        # Add type suffix to name
        if self.type is not None:
            name = name + '_' + self.type

        FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name, datapoints=datapoints, device_updated_cb=None)


    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_MEASURED_BRIGHTNESS) == dp or \
                self._datapoints.get(PID_RAIN_DETECTION) == dp or \
                self._datapoints.get(PID_OUTDOOR_TEMPERATURE) == dp or \
                self._datapoints.get(PID_WIND_SPEED) == dp:
            self.state = value
            LOG.info("sensor %s (%s) dp %s state %s", self.name, self.lookup_key, dp, value)

        else:
            LOG.info("sensor %s (%s) unknown dp %s value %s", self.name, self.lookup_key, dp, value)
    
    def update_parameter(self, param, value):
        LOG.debug("Not yet implemented")

