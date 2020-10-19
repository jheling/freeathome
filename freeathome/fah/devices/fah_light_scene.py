import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
        FUNCTION_IDS_SCENE,
        PID_SCENE_CONTROL,
    )

LOG = logging.getLogger(__name__)

# TODO: Add a FahTimerProfile class for timer profiles (function ID 4A00)
# Timer profiles may be switched on and off, so they are not exactly
# like scenes, but more like switches

class FahLightScene(FahDevice):
    """ Free@home scene   """

    def pairing_ids(function_id=None):
        if function_id in FUNCTION_IDS_SCENE:
            return {
                    "inputs": [],
                    "outputs": [
                        PID_SCENE_CONTROL,
                        ]
                    }

    async def activate(self):
        """ Activate the scene   """
        await self.client.set_datapoint(self.serialnumber, self.channel_id, 'odp0000', '1')

    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_SCENE_CONTROL) == dp:
            self.state = value
            LOG.info("scene %s (%s) is %s", self.name, self.lookup_key, self.state)
