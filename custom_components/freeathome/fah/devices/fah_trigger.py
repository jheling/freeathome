"""Devices that represent momentary free@home triggers."""

import logging

from .fah_device import FahDevice
from ..const import FUNCTION_IDS_TRIGGER, PID_TIMED_START_STOP

LOG = logging.getLogger(__name__)


class FahTrigger(FahDevice):
    """A free@home timed trigger."""

    @staticmethod
    def pairing_ids(function_id=None):
        """Return the datapoints used by trigger channels."""
        if function_id in FUNCTION_IDS_TRIGGER:
            return {
                "inputs": [PID_TIMED_START_STOP],
                "outputs": [],
            }
        return None

    async def press(self):
        """Send one trigger pulse and let free@home stop it."""
        await self.client.set_datapoint(
            self.serialnumber,
            self.channel_id,
            self._datapoints[PID_TIMED_START_STOP],
            "1",
        )

    def update_datapoint(self, dp, value):
        """Log trigger updates; triggers have no persistent state."""
        LOG.debug(
            "trigger %s (%s) dp %s value %s", self.name, self.lookup_key, dp, value
        )
