import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
        FUNCTION_IDS_BLIND_ACTUATOR,
        PID_MOVE_UP_DOWN,
        PID_ADJUST_UP_DOWN,
        PID_SET_ABSOLUTE_POSITION_BLINDS,
        PID_FORCE_POSITION_BLIND,
        PID_INFO_MOVE_UP_DOWN,
        PID_CURRENT_ABSOLUTE_POSITION_BLINDS_PERCENTAGE,
        PID_FORCE_POSITION_INFO,
    )

FORCE_POSITION_COMMANDS = {
        "none": "1",
        "open": "2",
        "closed": "3",
        }


FORCE_POSITION_STATES = {
        "0": "none",
        "2": "open",
        "3": "closed",
        }

LOG = logging.getLogger(__name__)

class FahCover(FahDevice):
    """ Free@Home cover device
    In freeathome the value 100 indicates that the cover is fully closed
    In home assistant the value 100 indicates that the cover is fully open
    """
    state = None
    position = None
    forced_position = None

    def pairing_ids(function_id=None):
        # TODO: Determine from function ID which pairing IDs are relevant
        # E.g. Slats -> Add slats data points
        if function_id in FUNCTION_IDS_BLIND_ACTUATOR:
            return {
                    "inputs": [
                        PID_MOVE_UP_DOWN,
                        PID_ADJUST_UP_DOWN,
                        PID_SET_ABSOLUTE_POSITION_BLINDS,
                        PID_FORCE_POSITION_BLIND,
                        ],
                    "outputs": [
                        PID_INFO_MOVE_UP_DOWN,
                        PID_CURRENT_ABSOLUTE_POSITION_BLINDS_PERCENTAGE,
                        PID_FORCE_POSITION_INFO,
                        ]
                    }

    def is_cover_closed(self):
        """ Return if the cover is closed   """
        return int(self.position) == 0

    def is_cover_opening(self):
        """ Return is the cover is opening   """
        return self.state == '2'

    def is_cover_closing(self):
        """ Return if the cover is closing   """
        return self.state == '3'

    def get_cover_position(self):
        """ Return the cover position """
        return int(self.position)

    def get_forced_cover_position(self):
        """Return forced cover position."""
        return FORCE_POSITION_STATES.get(self.forced_position)

    async def set_cover_position(self, position):
        """ Set the cover position  """
        dp = self._datapoints[PID_SET_ABSOLUTE_POSITION_BLINDS]
        await self.client.set_datapoint(self.serialnumber, self.channel_id, dp, str(abs(100 - position)))

    async def set_forced_cover_position(self, forced_position):
        """Set forced cover position."""
        dp = self._datapoints[PID_FORCE_POSITION_BLIND]
        if forced_position in FORCE_POSITION_COMMANDS:
            await self.client.set_datapoint(self.serialnumber, self.channel_id, dp, FORCE_POSITION_COMMANDS[forced_position])

    async def open_cover(self):
        """ Open the cover   """
        dp = self._datapoints[PID_MOVE_UP_DOWN]
        await self.client.set_datapoint(self.serialnumber, self.channel_id, dp, '0')

    async def close_cover(self):
        """ Close the cover   """
        dp = self._datapoints[PID_MOVE_UP_DOWN]
        await self.client.set_datapoint(self.serialnumber, self.channel_id, dp, '1')

    async def stop_cover(self):
        """ Stop the cover, only if it is moving """
        if (self.state == '2') or (self.state == '3'):
            dp = self._datapoints[PID_ADJUST_UP_DOWN]
            await self.client.set_datapoint(self.serialnumber, self.channel_id, dp, '1')

    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_INFO_MOVE_UP_DOWN) == dp:
            self.state = value
            LOG.info("cover device %s (%s) dp %s state %s", self.name, self.lookup_key, dp, self.state)

        elif self._datapoints.get(PID_CURRENT_ABSOLUTE_POSITION_BLINDS_PERCENTAGE) == dp:
            self.position = str(abs(100 - int(float(value))))
            LOG.info("cover device %s (%s) dp %s position %s", self.name, self.lookup_key, dp, value)

        elif self._datapoints.get(PID_FORCE_POSITION_INFO) == dp:
            self.forced_position = value
            LOG.info("cover device %s (%s) dp %s forced position %s", self.name, self.lookup_key, dp, value)

        else:
            LOG.info("cover device %s (%s) unknown dp %s value %s", self.name, self.lookup_key, dp, value)
