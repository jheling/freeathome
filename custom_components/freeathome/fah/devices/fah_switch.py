"""Devices that represent switches"""
import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
    FUNCTION_IDS_SWITCHING_ACTUATOR,
    PID_SWITCH_ON_OFF,
    PID_INFO_ON_OFF,
    )

LOG = logging.getLogger(__name__)

class FahSwitch(FahDevice):
    """ Free@Home switch object   """
    state = None

    def pairing_ids(function_id=None):
        if function_id in FUNCTION_IDS_SWITCHING_ACTUATOR:
            return {
                    "inputs": [
                        PID_SWITCH_ON_OFF,
                        ],
                    "outputs": [
                        PID_INFO_ON_OFF,
                        ]
                    }

    async def turn_on(self):
        """ Turn the switch on   """
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_SWITCH_ON_OFF], '1')
        self.state = True

    async def turn_off(self):
        """ Turn the switch off   """
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_SWITCH_ON_OFF], '0')
        self.state = False

    def is_on(self):
        """ Return the state of the switch   """
        return self.state

    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if PID_INFO_ON_OFF in self._datapoints and self._datapoints[PID_INFO_ON_OFF] == dp:
            self.state = (value == '1')
            LOG.info("switch device %s (%s) dp %s state %s", self.name, self.lookup_key, dp, value)

        else:
            LOG.info("switch device %s (%s) unknown dp %s value %s", self.name, self.lookup_key, dp, value)

    def update_parameter(self, param, value):
        LOG.debug("Not yet implemented")