import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
        FUNCTION_IDS_DOOR_OPENER,
        PID_LOCK_UNLOCK_COMMAND,
        PID_INFO_LOCK_UNLOCK,
    )

LOG = logging.getLogger(__name__)

class FahLock(FahDevice):
    """Free@home lock control via 7 inch panel"""
    state = None

    def pairing_ids(function_id=None):
        if function_id in FUNCTION_IDS_DOOR_OPENER:
            return {
                    "inputs": [
                        PID_LOCK_UNLOCK_COMMAND,
                        ],
                    "outputs": [
                        PID_INFO_LOCK_UNLOCK,
                        ]
                    }

    async def lock(self):
        dp = self._datapoints[PID_LOCK_UNLOCK_COMMAND]
        await self.client.set_datapoint(self.serialnumber, self.channel_id, dp, '0')

    async def unlock(self):
        dp = self._datapoints[PID_LOCK_UNLOCK_COMMAND]
        await self.client.set_datapoint(self.serialnumber, self.channel_id, dp, '1')

    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_INFO_LOCK_UNLOCK) == dp:
            self.state = value
            LOG.info("lock device %s (%s) dp %s state %s", self.name, self.lookup_key, dp, value)

        else:
            LOG.info("light device %s (%s) unknown dp %s value %s", self.name, self.lookup_key, dp, value)
