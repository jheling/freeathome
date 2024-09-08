import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
        FUNCTION_IDS_LIGHT_GROUP,
        PID_INFO_ON_OFF,
        PID_INFO_ACTUAL_DIMMING_VALUE,
        PID_SYSAP_INFO_ON_OFF,
        PID_SYSAP_INFO_ACTUAL_DIMMING_VALUE,
        PID_SWITCH_ON_OFF,
        PID_ABSOLUTE_SET_VALUE,
    )

LOG = logging.getLogger(__name__)

class FahLightGroup(FahDevice):
    """ Free@home light group """
    state = None
    brightness = None

    def pairing_ids(function_id=None):
        if function_id in FUNCTION_IDS_LIGHT_GROUP:
            return {
                    "inputs": [
                        PID_INFO_ON_OFF,
                        PID_INFO_ACTUAL_DIMMING_VALUE,
                    ],
                    "outputs": [
                        PID_SYSAP_INFO_ON_OFF,
                        PID_SWITCH_ON_OFF,
                        PID_SYSAP_INFO_ACTUAL_DIMMING_VALUE,
                        PID_ABSOLUTE_SET_VALUE,
                        ]
                    }

    async def turn_on(self):
        """ Turn the light on   """
        oldstate = self.state
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_INFO_ON_OFF], '1')
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_SWITCH_ON_OFF], '1')
        self.state = True

        if self.is_dimmer() \
                and ((oldstate != self.state and int(self.brightness) > 0) or (oldstate == self.state)):
            await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_INFO_ACTUAL_DIMMING_VALUE], str(self.brightness))
            await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_ABSOLUTE_SET_VALUE], str(self.brightness))

    async def turn_off(self):
        """ Turn the light off   """
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_INFO_ON_OFF], '0')
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_SWITCH_ON_OFF], '0')
        self.state = False

    def set_brightness(self, brightness):
        """ Set the brightness of the light  """
        if self.is_dimmer():
            self.brightness = brightness

    def get_brightness(self):
        """ Return the brightness of the light  """
        return self.brightness

    def is_on(self):
        """ Return the state of the light   """
        return self.state

    def is_dimmer(self):
        """Return true if device is a dimmer"""
        return PID_ABSOLUTE_SET_VALUE in self._datapoints

    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if PID_SYSAP_INFO_ON_OFF in self._datapoints and self._datapoints[PID_SYSAP_INFO_ON_OFF] == dp:
            self.state = (value == '1')
            LOG.info("light group %s (%s) dp %s state %s", self.name, self.lookup_key, dp, value)

        elif PID_SYSAP_INFO_ACTUAL_DIMMING_VALUE in self._datapoints and self._datapoints[PID_SYSAP_INFO_ACTUAL_DIMMING_VALUE] == dp:
            self.brightness = value
            LOG.info("light group %s (%s) dp %s brightness %s", self.name, self.lookup_key, dp, value)

        else:
            LOG.info("light group %s (%s) unknown dp %s value %s", self.name, self.lookup_key, dp, value)

    def update_parameter(self, param, value):
        LOG.debug("Not yet implemented")
