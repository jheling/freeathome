import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
        FUNCTION_IDS_MOVEMENT_DETECTOR,
        PID_MEASURED_BRIGHTNESS,
        )

LOG = logging.getLogger(__name__)

def sensor_type_from_pairing_ids(datapoints):
    for pairing_id, dp in datapoints.items():
        if pairing_id == PID_MEASURED_BRIGHTNESS:
            return "lux"


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


    def __init__(self, client, device_info, serialnumber, channel_id, name, datapoints={}, device_updated_cb=None):
        # Determine sensor type (e.g. temperature, brightness) from datapoints
        self.type = sensor_type_from_pairing_ids(datapoints)

        # Add type suffix to name
        if self.type is not None:
            name = name + '_' + self.type

        FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name, datapoints=datapoints, device_updated_cb=None)


    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_MEASURED_BRIGHTNESS) == dp:
            self.state = value
            LOG.info("sensor %s (%s) dp %s state %s", self.name, self.lookup_key, dp, value)

        else:
            LOG.info("sensor %s (%s) unknown dp %s value %s", self.name, self.lookup_key, dp, value)
