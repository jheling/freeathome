import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
        FUNCTION_IDS_SENSOR_UNIT,
        FUNCTION_IDS_MOVEMENT_DETECTOR,
        PID_SWITCH_ON_OFF,
        PID_PRESENCE,
        )

LOG = logging.getLogger(__name__)

class FahBinarySensor(FahDevice):
    """Free@Home binary object """
    state = None

    def pairing_ids(function_id=None):
        if function_id in FUNCTION_IDS_SENSOR_UNIT:
            return {
                    "inputs": [],
                    "outputs": [
                        PID_SWITCH_ON_OFF,
                        ]
                    }

        elif function_id in FUNCTION_IDS_MOVEMENT_DETECTOR:
            return {
                    "inputs": [],
                    "outputs": [
                        PID_PRESENCE,
                        ]
                    }

    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_SWITCH_ON_OFF) == dp or \
                self._datapoints.get(PID_PRESENCE) == dp:
            self.state = value
            LOG.debug("binary sensor device %s dp %s state %s", self.lookup_key, dp, value)
