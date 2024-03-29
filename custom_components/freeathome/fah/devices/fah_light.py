"""Devices that represent lights"""
import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
    FUNCTION_IDS_SWITCHING_ACTUATOR,
    FUNCTION_IDS_DIMMING_ACTUATOR,
    FUNCTION_IDS_COLOR_ACTUATOR,
    FUNCTION_IDS_COLOR_TEMP_ACTUATOR,
    PID_SWITCH_ON_OFF,
    PID_ABSOLUTE_SET_VALUE,
    PID_INFO_ON_OFF,
    PID_INFO_ACTUAL_DIMMING_VALUE,
    PID_COLOR_TEMPERATURE,
    PID_INFO_COLOR_TEMPERATURE,
    PID_HSV,
    PID_INFO_HSV,
    PID_RGB,
    PID_INFO_RGB,
    PID_COLOR,
    PID_SATURATION,
    PAR_MAXIMUM_COLOR_TEMPERATURE,
    PAR_MINIMUM_COLOR_TEMPERATURE,
    )

LOG = logging.getLogger(__name__)

class FahLight(FahDevice):
    """ Free@Home light object   """
    state = None
    brightness = None
    color_temp = None 
    rgb_color = None
    max_color_temp = None
    min_color_temp = None


    def __init__(self, client, device_info, serialnumber, channel_id, name, datapoints={}, parameters={}, device_updated_cb=None):
        # Determine minimum and maximum value for color temperature
        if PID_COLOR_TEMPERATURE in datapoints:
            if PAR_MAXIMUM_COLOR_TEMPERATURE in parameters:
                self.max_color_temp = parameters[PAR_MAXIMUM_COLOR_TEMPERATURE]
            if PAR_MINIMUM_COLOR_TEMPERATURE in parameters:
                self.min_color_temp = parameters[PAR_MINIMUM_COLOR_TEMPERATURE]    

        FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name, datapoints=datapoints, parameters=parameters, device_updated_cb=None)


    def pairing_ids(function_id=None, switch_as_x=False):

        if function_id in FUNCTION_IDS_COLOR_ACTUATOR:
            return {
                    "inputs": [
                        PID_SWITCH_ON_OFF,
                        PID_ABSOLUTE_SET_VALUE,
                        PID_RGB,
                        ],
                    "outputs": [
                        PID_INFO_ON_OFF,
                        PID_INFO_ACTUAL_DIMMING_VALUE,
                        PID_INFO_RGB,
                        ]
            }

        if function_id in FUNCTION_IDS_COLOR_TEMP_ACTUATOR:
            return {
                    "inputs": [
                        PID_SWITCH_ON_OFF,
                        PID_ABSOLUTE_SET_VALUE,
                        PID_COLOR_TEMPERATURE,                        
                        ],
                    "outputs": [
                        PID_INFO_ON_OFF,
                        PID_INFO_ACTUAL_DIMMING_VALUE,
                        PID_INFO_COLOR_TEMPERATURE,
                        ]
            }            

        if function_id in FUNCTION_IDS_DIMMING_ACTUATOR:
            return {
                    "inputs": [
                        PID_SWITCH_ON_OFF,
                        PID_ABSOLUTE_SET_VALUE,
                        ],
                    "outputs": [
                        PID_INFO_ON_OFF,
                        PID_INFO_ACTUAL_DIMMING_VALUE,
                        ]
                    }
        # If switch_as_x is False, we want to treat the switching actuator as a light
        elif function_id in FUNCTION_IDS_SWITCHING_ACTUATOR and not switch_as_x:
            return {
                    "inputs": [
                        PID_SWITCH_ON_OFF,
                        ],
                    "outputs": [
                        PID_INFO_ON_OFF,
                        ]
                    }
        
    def parameter_ids(function_id=None):
        if function_id in FUNCTION_IDS_COLOR_TEMP_ACTUATOR:
            return {
                    "parameters": [
                        PAR_MAXIMUM_COLOR_TEMPERATURE,
                        PAR_MINIMUM_COLOR_TEMPERATURE,
                        ]
                    }    

    async def turn_on(self):
        """ Turn the light on   """
        oldstate = self.state
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_SWITCH_ON_OFF], '1')
        self.state = True

        if self.is_dimmer() \
                and ((oldstate != self.state and int(self.brightness) > 0) or (oldstate == self.state)):
            await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_ABSOLUTE_SET_VALUE], str(self.brightness))

        if self.is_color_temp():
            await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_COLOR_TEMPERATURE], str(self.color_temp))

        if self.is_rgb():
            await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_RGB], str(self.rgb_color))

    async def turn_off(self):
        """ Turn the light off   """
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_SWITCH_ON_OFF], '0')
        self.state = False

    def set_brightness(self, brightness):
        """ Set the brightness of the light 0 - 100% """
        if self.is_dimmer():
            self.brightness = brightness

    def get_brightness(self):
        """ Return the brightness of the light  """
        return self.brightness

    def set_color_temp(self, color_temp):
        """Set the color temp of the light. Input in Kelvin, internal in 0 - 100 %"""
        if self.is_color_temp():
            if color_temp == self.min_color_temp:
                self.color_temp = 0
            elif color_temp == self.max_color_temp:
                self.color_temp = 100
            else:
                self.color_temp = int( (color_temp - self.min_color_temp ) / (self.max_color_temp - self.min_color_temp ))

    def get_color_temp(self):
        """ Get the color temp internal 0-100% , output in Kelvin """
        if self.color_temp == 0:
            return self.min_color_temp
        elif self.color_temp == 100:
            return self.max_color_temp
        else:
            return int(self.color_temp * (self.max_color_temp - self.min_color_temp) + self.min_color_temp)
    
    def set_rgb_color(self, red, green, blue):
        if self.is_rgb():
            self.rgb_color = (red<<16) + (green<<8) + blue
        
    def get_rgb_color(self): 
        blue =  self.rgb_color & 255
        green = (self.rgb_color >> 8) & 255
        red =   (self.rgb_color >> 16) & 255
        return red, green, blue

    def is_on(self):
        """ Return the state of the light   """
        return self.state

    def is_dimmer(self):
        """Return true if device is a dimmer"""
        return PID_ABSOLUTE_SET_VALUE in self._datapoints
    
    def is_color_temp(self):
        return PID_COLOR_TEMPERATURE in self._datapoints

    def is_rgb(self):
        return PID_RGB in self._datapoints

    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if PID_INFO_ON_OFF in self._datapoints and self._datapoints[PID_INFO_ON_OFF] == dp:
            self.state = (value == '1')
            LOG.info("light device %s (%s) dp %s state %s", self.name, self.lookup_key, dp, value)

        elif PID_INFO_ACTUAL_DIMMING_VALUE in self._datapoints and self._datapoints[PID_INFO_ACTUAL_DIMMING_VALUE] == dp:
            self.brightness = value
            LOG.info("light device %s (%s) dp %s brightness %s", self.name, self.lookup_key, dp, value)

        elif PID_INFO_COLOR_TEMPERATURE in self._datapoints and self._datapoints[PID_INFO_COLOR_TEMPERATURE] == dp:
            self.color_temp = int(value)
            LOG.info("light device %s (%s) dp %s color temperature %s", self.name, self.lookup_key, dp, value)

        elif PID_INFO_RGB in self._datapoints and self._datapoints[PID_INFO_RGB] == dp:
            self.rgb_color = int(value)
            LOG.info("light device %s (%s) dp %s rgb color %s", self.name, self.lookup_key, dp, value)

        else:
            LOG.info("light device %s (%s) unknown dp %s value %s", self.name, self.lookup_key, dp, value)
            
    def update_parameter(self, param, value):
        LOG.debug("Not yet implemented")
