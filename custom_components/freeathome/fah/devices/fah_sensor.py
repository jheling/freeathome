import asyncio
import logging

from .fah_device import FahDevice
from ..const import (
        FUNCTION_IDS_MOVEMENT_DETECTOR,
        FUNCTION_IDS_WEATHER_STATION,
        FUNCTION_IDS_AIR_QUALITY_SENSOR,
        PID_MEASURED_BRIGHTNESS,
        PID_OUTDOOR_TEMPERATURE,
        PID_WIND_SPEED,
        PID_RAIN_ALARM,
        PID_MEASURED_HUMIDITY,
        PID_MEASURED_VOC,
        PID_MEASURED_CO2
        )

LOG = logging.getLogger(__name__)

def sensor_type_from_pairing_ids(datapoints):
    for pairing_id, dp in datapoints.items():
        if dp is None:
            continue

        if pairing_id == PID_MEASURED_BRIGHTNESS:
            return "lux"
        elif pairing_id == PID_RAIN_ALARM:
            return "rain"
        elif pairing_id == PID_OUTDOOR_TEMPERATURE:
            return "temperature"
        elif pairing_id == PID_WIND_SPEED:
            return "windstrength"
        elif pairing_id == PID_MEASURED_HUMIDITY:
            return "humidity"
        elif pairing_id == PID_MEASURED_VOC:
            return "voc"
        elif pairing_id == PID_MEASURED_CO2:
            return "co2"


AIR_QUALITY_PIDS = {PID_MEASURED_HUMIDITY, PID_MEASURED_VOC, PID_MEASURED_CO2}


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
                        PID_RAIN_ALARM,
                        ]
                    }

        elif function_id in FUNCTION_IDS_AIR_QUALITY_SENSOR:
            return {
                    "inputs": [],
                    "outputs": AIR_QUALITY_PIDS
                    }


    def __init__(self, client, device_info, serialnumber, channel_id, name, datapoints={}, parameters={}, device_updated_cb=None):
        # Determine sensor type (e.g. temperature, brightness) from datapoints
        self.type = sensor_type_from_pairing_ids(datapoints)

        # Add type suffix to name
        if self.type is not None:
            name = name + '_' + self.type

        FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name, datapoints=datapoints, parameters=parameters, device_updated_cb=None)


    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_MEASURED_BRIGHTNESS) == dp or \
                self._datapoints.get(PID_RAIN_ALARM) == dp or \
                self._datapoints.get(PID_OUTDOOR_TEMPERATURE) == dp or \
                self._datapoints.get(PID_WIND_SPEED) == dp or \
                self._datapoints.get(PID_MEASURED_HUMIDITY) == dp or \
                self._datapoints.get(PID_MEASURED_VOC) == dp or \
                self._datapoints.get(PID_MEASURED_CO2) == dp:
            self.state = value
            LOG.info("sensor %s (%s) dp %s state %s", self.name, self.lookup_key, dp, value)

        else:
            LOG.info("sensor %s (%s) unknown dp %s value %s", self.name, self.lookup_key, dp, value)
    
    def update_parameter(self, param, value):
        LOG.debug("Not yet implemented")

    @property
    def lookup_key(self):
        """Return device lookup key"""
        lookup_key = super().lookup_key

        # make unique lookup_key because PID_MEASURED_HUMIDITY, PID_MEASURED_VOC, PID_MEASURED_CO2 are all on the
        # save device & channel, but are separate sensors.
        if len(self._datapoints) == 1 and list(self._datapoints.keys())[0] in AIR_QUALITY_PIDS:
            lookup_key += "/" + list(self._datapoints.values())[0]

        return lookup_key
