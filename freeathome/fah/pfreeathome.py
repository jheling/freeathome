#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Interface for accessing Free@Home
"""
import asyncio
import logging
# import urllib.request
# import json
import xml.etree.ElementTree as ET
import slixmpp
import zlib
import sys

from packaging import version
from slixmpp import Message
from slixmpp.xmlstream import ElementBase, ET, register_stanza_plugin
from slixmpp.plugins.xep_0009.binding import py2xml, xml2py
from slixmpp.plugins.xep_0009.stanza.RPC import RPCQuery, MethodCall, MethodResponse
from slixmpp.plugins.xep_0060.stanza.pubsub_event import Event, EventItems, EventItem
from slixmpp.exceptions import IqError
from slixmpp import Iq
from .const import (
    FUNCTION_IDS_SENSOR_UNIT,
    FUNCTION_IDS_SWITCHING_ACTUATOR,
    FUNCTION_IDS_DIMMING_ACTUATOR,
    FUNCTION_IDS_BLIND_ACTUATOR,
    FUNCTION_IDS_SCENE,
    FUNCTION_IDS_ROOM_TEMPERATURE_CONTROLLER,
    NAME_IDS_TO_BINARY_SENSOR_SUFFIX,
    PID_SWITCH_ON_OFF,
    PID_ABSOLUTE_SET_VALUE,
    PID_INFO_ON_OFF,
    PID_INFO_ACTUAL_DIMMING_VALUE,
    PID_MOVE_UP_DOWN,
    PID_ADJUST_UP_DOWN,
    PID_SET_ABSOLUTE_POSITION_BLINDS,
    PID_FORCE_POSITION_BLIND,
    PID_INFO_MOVE_UP_DOWN,
    PID_CURRENT_ABSOLUTE_POSITION_BLINDS_PERCENTAGE,
    PID_FORCE_POSITION_INFO,
    PID_ECO_MODE_ON_OFF_REQUEST,
    PID_CONTROLLER_ON_OFF_REQUEST,
    PID_ABSOLUTE_SETPOINT_TEMPERATURE,
    PID_SET_VALUE_TEMPERATURE,
    PID_CONTROLLER_ON_OFF,
    PID_STATUS_INDICATION,
    PID_MEASURED_TEMPERATURE,
    PID_HEATING_DEMAND,
    )
from .messagereader import MessageReader
from .settings import SettingsFah
from .saslhandler import SaslHandler

LOG = logging.getLogger(__name__)


class ItemUpdate(ElementBase):
    """ part of the xml message  """
    namespace = 'http://abb.com/protocol/update'
    name = 'update'
    plugin_attrib = name
    interfaces = set('data')


class ItemUpdateEncrypted(ElementBase):
    namespace = 'http://abb.com/protocol/update_encrypted'
    name = 'update'
    plugin_attrib = name
    interfaces = set('data')


def data2py(update):
    """ Convert xml to  a list of args """
    namespace = 'http://abb.com/protocol/update'
    vals = []
    for data in update.xml.findall('{%s}data' % namespace):
        vals.append(data.text)
    return vals


def message2py(mes):
    namespace = 'http://abb.com/protocol/update_encrypted'
    vals = []
    for data in mes.xml.findall('{%s}data' % namespace):
        vals.append(data.text)
    return vals


class FahDevice:
    """ Free@Home base object """

    def __init__(self, client, device_info, serialnumber, channel_id, name, datapoints={}, device_updated_cb=None):
        self._device_info = device_info
        self._serialnumber = serialnumber
        self._channel_id = channel_id
        self._name = name
        self._client = client
        self._device_updated_cbs = []
        self._datapoints = datapoints
        if device_updated_cb is not None:
            self.register_device_updated_cb(device_updated_cb)

    def register_device_updated_cb(self, device_updated_cb):
        """Register device updated callback."""
        self._device_updated_cbs.append(device_updated_cb)

    def unregister_device_cb(self, device_updated_cb):
        """Unregister device updated callback."""
        self._device_updated_cbs.remove(device_updated_cb)

    async def after_update(self):
        """Execute callbacks after internal state has been changed."""
        for device_updated_cb in self._device_updated_cbs:
            await device_updated_cb(self)

    @property
    def serialnumber(self):
        """ return the serial number """
        return self._serialnumber

    @property
    def channel_id(self):
        """Return channel id"""
        return self._channel_id

    @property
    def name(self):
        """ return the name of the device   """
        return self._name

    @property
    def client(self):
        """ return the Client object """
        return self._client

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info

    @property
    def lookup_key(self):
        """Return device lookup key"""
        return self.serialnumber + "/" + self.channel_id

class FahSensor(FahDevice):
    """ Free@Home sensor object """
    state = None     
    output_device = None    

    def __init__(self, client, device_info, serialnumber, channel_id, name, sensor_type, state, output_device):
        FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name)
        self.type = sensor_type
        self.state = state        
        self.output_device = output_device

class FahBinarySensor(FahDevice):
    """Free@Home binary object """
    state = None
    output_device = None

    def __init__(self, client, device_info, serialnumber, channel_id, name, state=False, output_device='odp0000'):
        FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name)
        self.state = state
        self.output_device = output_device

class FahLock(FahDevice):
    """" Free@home lock controll in 7 inch panel """
    state = None

    def __init__(self, client, device_info, serialnumber, channel_id, name, state=False):
        FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name)
        self.state = state        

    async def lock(self):
        await self.client.set_datapoint(self.serialnumber, self.channel_id, 'idp0000', '0')
    
    async def unlock(self):
        await self.client.set_datapoint(self.serialnumber, self.channel_id, 'idp0000', '1')

class FahThermostat(FahDevice):
    """Free@Home thermostat """
    current_temperature = None
    current_actuator = None
    target_temperature = None

    def pairing_ids(function_id=None):
        return {
                "inputs": [
                    PID_ECO_MODE_ON_OFF_REQUEST,
                    PID_CONTROLLER_ON_OFF_REQUEST,
                    PID_ABSOLUTE_SETPOINT_TEMPERATURE,
                    ],
                "outputs": [
                    PID_SET_VALUE_TEMPERATURE,
                    PID_CONTROLLER_ON_OFF,
                    PID_STATUS_INDICATION,
                    PID_MEASURED_TEMPERATURE,
                    PID_HEATING_DEMAND,
                    ]
                }

    async def turn_on(self):
        """ Turn the thermostat on   """
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_ECO_MODE_ON_OFF_REQUEST], '0')
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_CONTROLLER_ON_OFF_REQUEST], '1')

    async def turn_off(self):
        """ Turn the thermostat off   """
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_CONTROLLER_ON_OFF_REQUEST], '0')

    async def eco_mode(self):
        """ Put the thermostat in eco mode   """
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_ECO_MODE_ON_OFF_REQUEST], '2')

    async def set_target_temperature(self, temperature):
        await self.client.set_datapoint(self.serialnumber, self.channel_id, self._datapoints[PID_ABSOLUTE_SETPOINT_TEMPERATURE], '%.2f' % temperature)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state == '1'

    @property
    def ecomode(self):
        return self._eco_mode

    @ecomode.setter
    def ecomode(self, eco_mode):
        self._eco_mode = eco_mode == '68'

    def update_datapoint(self, dp, value):
        """Receive updated datapoint."""
        if self._datapoints.get(PID_SET_VALUE_TEMPERATURE) == dp:
            self.target_temperature = value
            LOG.info("thermostat device %s target temp is %s", self.lookup_key, value)

        elif self._datapoints.get(PID_CONTROLLER_ON_OFF) == dp:
            self.state = value
            LOG.info("thermostat device %s state is %s", self.lookup_key, value)

        elif self._datapoints.get(PID_STATUS_INDICATION) == dp:
            self.ecomode = value
            LOG.info("thermostat device %s eco mode is %s", self.lookup_key, value)

        elif self._datapoints.get(PID_MEASURED_TEMPERATURE) == dp:
            self.current_temperature = value
            LOG.info("thermostat device %s current temp is %s", self.lookup_key, value)

        elif self._datapoints.get(PID_HEATING_DEMAND) == dp:
            self.current_actuator = value
            LOG.info("thermostat device %s current heating actuator state is %s", self.lookup_key, value)


class FahLight(FahDevice):
    """ Free@Home light object   """
    state = None
    light_type = None
    brightness = None

    def pairing_ids(function_id=None):
        # TODO: Determine from function ID which pairing IDs are relevant
        # E.g. dimmer -> Adds absolute set value and actual dimming value
        return {
                "inputs": [
                    PID_SWITCH_ON_OFF,
                    ],
                "outputs": [
                    PID_INFO_ON_OFF,
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

    async def turn_off(self):
        """ Turn the light off   """
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
        if PID_INFO_ON_OFF in self._datapoints and self._datapoints[PID_INFO_ON_OFF] == dp:
            self.state = (value == '1')
            LOG.info("device %s (%s) is %s",
                     self.name, self.lookup_key, self.state)

        elif PID_INFO_ACTUAL_DIMMING_VALUE in self._datapoints and self._datapoints[PID_INFO_ACTUAL_DIMMING_VALUE] == dp:
            self.brightness = value
            LOG.info("device %s (%s) brightness %s",
                     self.name, self.lookup_key,
                     self.brightness)


class FahLightScene(FahDevice):
    """ Free@home scene   """

    def __init__(self, client, device_info, serialnumber, channel_id, name):
        FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name)

    async def activate(self):
        """ Activate the scene   """
        await self.client.set_datapoint(self.serialnumber, self.channel_id, 'odp0000', '1')


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
        return int(self.forced_position)

    async def set_cover_position(self, position):
        """ Set the cover position  """
        dp = self._datapoints[PID_SET_ABSOLUTE_POSITION_BLINDS]
        await self.client.set_datapoint(self.serialnumber, self.channel_id, dp, str(abs(100 - position)))

    async def set_forced_cover_position(self, forced_position):
        """Set forced cover position."""
        dp = self._datapoints[PID_FORCE_POSITION_BLIND]
        await self.client.set_datapoint(self.serialnumber, self.channel_id, dp, str(forced_position))

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
            LOG.info("device %s (%s) is %s",
                     self.name, self.lookup_key, self.state)

        elif self._datapoints.get(PID_CURRENT_ABSOLUTE_POSITION_BLINDS_PERCENTAGE) == dp:
            self.position = str(abs(100 - int(float(value))))
            LOG.info("device %s (%s) position %s",
                     self.name, self.lookup_key,
                     self.position)

        elif self._datapoints.get(PID_FORCE_POSITION_INFO) == dp:
            self.forced_position = value


def get_room_names(xmlroot):
    """ Return the floors and rooms of the installation   """
    floorplan = xmlroot.find('floorplan')
    floornames = {}
    roomnames = {}

    for floor in floorplan.findall('floor'):
        floor_name = floor.get('name')
        floor_uid = floor.get('uid')
        floornames[floor_uid] = floor_name

        roomnames[floor_uid] = {}
        for room in floor.findall('room'):
            room_name = room.get('name')
            room_uid = room.get('uid')
            roomnames[floor_uid][room_uid] = room_name

    return roomnames


def get_names(xmlroot):
    strings = xmlroot.find('strings')
    result = {}

    for string in strings.findall('string'):
        name_id = string.get('nameId')
        name = string.text
        result[name_id] = name

    return result

def get_attribute(xmlnode, name):
    """ Return an attribute value (xml)   """
    for attributes in xmlnode.findall('attribute'):
        if attributes.get('name') == name:
            return attributes.text
    return ''


def get_input_datapoint(xmlnode, input_name):
    """ Return an input point value (xml)   """
    inputs = xmlnode.find('inputs')
    for datapoints in inputs.findall('dataPoint'):
        if datapoints.get('i') == input_name:
            return datapoints.find('value').text
    return None


def get_output_datapoint(xmlnode, output_name):
    """ Return an output point value (xml)   """
    outputs = xmlnode.find('outputs')
    for datapoints in outputs.findall('dataPoint'):
        if datapoints.get('i') == output_name:
            return datapoints.find('value').text
    return None


def get_datapoint_by_pairing_id(xmlnode, type, pairing_id):
    """Returns output datapoint by pairing id."""
    for datapoint in xmlnode.find(type).findall('dataPoint'):
        # TODO: Hack: skip invalid (e.g. measured temperature for climate)
        if datapoint.find('value').text == 'invalid':
            continue
        if int(datapoint.get('pairingId'), 16) == pairing_id:
            return datapoint.get('i')

    return None


def get_datapoints_by_pairing_ids(xmlnode, pairing_ids):
    """Returns a dict with pairing id as key and datapoint number as value."""
    datapoints = {}
    for type, pairing_ids_for_type in pairing_ids.items():
        for pairing_id in pairing_ids_for_type:
            datapoints[pairing_id] = get_datapoint_by_pairing_id(xmlnode, type, pairing_id)

    return datapoints


class Client(slixmpp.ClientXMPP):
    """ Client for connecting to the free@home sysap   """
    found_devices = False
    connect_finished = False
    authenticated = False
    use_room_names = False
    connect_in_error = False

    # The specific devices
    devices = {}
    monitored_datapoints = {}

    switch_type_1 = {
        '1': [0],  # Normal switch  (channel 0)
        '2': [1, 2]  # Impuls switch  (channel 1,2)
    }

    switch_type_2 = {
        '1': [0, 3],  # Left switch, right switch (channel 0,3 )
        '2': [0, 4, 5],  # Left switch, right impuls (channel 0,4,5)
        '3': [1, 2, 3],  # Left impuls, right switch (channel 1,2,3)
        '4': [1, 2, 4, 5]  # Left impuls, right impuls (channel 1,2,4,5)
    }

    binary_function_output = {
        '0':'0', '1':'0', '3':'2', '4':'4', '5':'5','28':'6', '2a':'7' ,
        '6':'8', 'c':'9', 'd':'A', 'e':'B', 'f':'C', '11':'D'
        }
          
    weatherstation_function_output = { 
        '41':'odp0001', '42':'odp0000', '43':'odp0001', '44':'odp0003'
        }
          
    def __init__(self, jid, password, host, port, fahversion, iterations=None, salt=None, reconnect=True):
        """ x   """
        slixmpp.ClientXMPP.__init__(self, jid, password, sasl_mech='SCRAM-SHA-1')

        self.fahversion = fahversion
        self.x_jid = jid
        self._host = host
        self._port = port
        self.reconnect = reconnect

        LOG.info(' version: %s', self.fahversion)

        self.password = password
        self.iterations = iterations
        self.salt = salt

        if version.parse(self.fahversion) >= version.parse("2.3.0"):
            self.saslhandler = SaslHandler(self, self.jid, self.password, self.iterations, self.salt)

        import os
        import binascii
        self.requested_jid.resource = binascii.b2a_hex(os.urandom(4))

        # handle session_start and message events
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("roster_update", self.roster_callback)
        self.add_event_handler("pubsub_publish", self.pub_sub_callback)
        self.add_event_handler("failed_auth", self.failed_auth)
        self.add_event_handler("disconnected", self._disconnected)
        
        # register plugins
        self.register_plugin('xep_0030')  # RPC
        self.register_plugin('xep_0060')  # PubSub
        self.register_plugin('xep_0199', {'keepalive': True, 'frequency': 60})  # ping

        
        register_stanza_plugin(Iq, RPCQuery)
        register_stanza_plugin(RPCQuery, MethodCall)
        register_stanza_plugin(RPCQuery, MethodResponse)

        register_stanza_plugin(Message, Event)
        register_stanza_plugin(Event, EventItems)
        register_stanza_plugin(EventItems, EventItem, iterable=True)
        register_stanza_plugin(EventItem, ItemUpdate)
        register_stanza_plugin(EventItem, ItemUpdateEncrypted)

    async def _disconnected(self, event):
        """ If connection is lost, try to reconnect """
        LOG.info("Connection with SysAP lost")
        self.connect_in_error = True
        if not self.reconnect:
            return

        await asyncio.sleep(2)

        if version.parse(self.fahversion) >= version.parse("2.3.0"):
            self.saslhandler = SaslHandler(self, self.jid, self.password, self.iterations, self.salt)

        self.sysap_connect()

    def connecting_in_error(self):
        """For checking if connection is in error or not"""
        return self.connect_in_error

    def sysap_connect(self):
        super(Client, self).connect((self._host, self._port))


    def connect_ready(self):
        """ Polling if the connection process is ready   """
        return self.connect_finished

    # pylint: disable=unused-argument
    async def start(self, event):
        """ Send precence and Roster (xmpp) """

        if version.parse(self.fahversion) >= version.parse("2.3.0"):
            await self.saslhandler.initiate_key_exchange()

            # The connect has succeeded
        self.authenticated = True

        featurelist = ['http://jabber.org/protocol/caps', 'http://jabber.org/protocol/disco#info']
        if version.parse(self.fahversion) >= version.parse("2.3.0"):
            featurelist.extend(
                ['http://abb.com/protocol/update_encrypted', 'http://abb.com/protocol/update_encrypted+notify',
                 'http://abb.com/protocol/log_encrypted', 'http://abb.com/protocol/log_encrypted+notify'])
            capsversion = 'http://gonicus.de/caps#1.1'
        else:
            featurelist.extend(['http://abb.com/protocol/update', 'http://abb.com/protocol/update+notify',
                                'http://abb.com/protocol/log', 'http://abb.com/protocol/log+notify'])
            capsversion = 'http://gonicus.de/caps#1.0'
        features = {'features': featurelist}

        identity = {'category': 'client', 'itype': 'pc', 'name': 'QxXmpp/JSJaC client'}

        self['xep_0030'].static.add_identity(self.boundjid.full, capsversion, '', identity)
        self['xep_0030'].static.set_features(self.boundjid.full, capsversion, '', features)

        LOG.info('send presence')
        self.send_presence()

        self.send_presence_subscription(pto="mrha@busch-jaeger.de/rpc", pfrom=self.boundjid.full)

        if version.parse(self.fahversion) >= version.parse("2.3.0"):
            self.send('<presence xmlns="jabber:client"><c xmlns="http://jabber.org/protocol/caps"'
                      ' ver="1.1" node="http://gonicus.de/caps"/></presence>')
        else:
            self.send('<presence xmlns="jabber:client"><c xmlns="http://jabber.org/protocol/caps"'
                      ' ver="1.0" node="http://gonicus.de/caps"/></presence>')

        LOG.info('get roster')
        self.get_roster()

    def failed_auth(self, event):
        """ If the password in the config is wrong  """
        LOG.error('Free@Home : authentication failed, probably wrong password')
        self.connect_finished = True

    async def set_datapoint(self, serialnumber, channel_id, datapoint, command):
        """ Send a command to the sysap   """
        LOG.info("set_datapoint %s/%s %s %s", serialnumber, channel_id, datapoint, command)

        name = serialnumber + '/' + channel_id + '/' + datapoint

        try:
            await self.send_rpc_iq('RemoteInterface.setDatapoint',
                                   name, command, callback=self.rpc_callback)
        except IqError as error:
            raise error

    def send_rpc_iq(self, command, *argv, timeout=None, callback=None, timeout_callback=None):
        """ Compose a specific message  """

        my_iq = self.make_iq_set()
        my_iq['to'] = 'mrha@busch-jaeger.de/rpc'
        my_iq['from'] = self.boundjid.full
        my_iq.enable('rpc_query')
        my_iq['rpc_query']['method_call']['method_name'] = command
        my_iq['rpc_query']['method_call']['params'] = py2xml(*argv)

        return my_iq.send(timeout=timeout, callback=callback, timeout_callback=timeout_callback)

    def filter_devices(self, device_class):
        """Returns list of devices, filtered by a specific device class."""
        return dict(filter(lambda el: isinstance(el[1], device_class), self.devices.items()))

    def get_devices(self, device_type):
        """ After all the devices have been extracted from the xml file,
        the lists with device objects are returned to HA
        """
        return_type = {}

        if device_type == 'light':
            return self.filter_devices(FahLight)

        # if device_type == 'scene':
        #     return_type = self.scene_devices

        if device_type == 'cover':
            return self.filter_devices(FahCover)

        # if device_type == 'binary_sensor':
        #     return_type = self.binary_devices

        if device_type == 'thermostat':
            return self.filter_devices(FahThermostat)

        # if device_type == 'sensor':
        #     return_type = self.sensor_devices

        # if device_type == 'lock':
        #     return_type = self.lock_devices

        return return_type

    def roster_callback(self, roster_iq):
        """ If the roster callback is called, the initial connection has finished  """
        LOG.info("Roster callback ")
        self.connect_finished = True

    def rpc_callback(self, my_iq):
        """ Capture messages returning from the sysap  """
        my_iq.enable('rpc_query')

        if my_iq['rpc_query']['method_response']['fault'] is not None:
            fault = my_iq['rpc_query']['method_response']['fault']
            LOG.info(fault['string'])
        else:
            result = xml2py(my_iq['rpc_query']['method_response']['params'])
            LOG.info('method response: %s', result[0])

    async def pub_sub_callback(self, msg):
        """ Process the device update messages of the sysap   """
        # pylint: disable=too-many-nested-blocks
        args = None

        items = msg.xml.find(".//*[@node='http://abb.com/protocol/update_encrypted']")
        if items is not None:
            # This message is encrypted
            if msg['pubsub_event']['items']['item']['update']['data'] is not None:

                args = message2py(msg['pubsub_event']['items']['item']['update'])

                if args:

                    xmessage = self.saslhandler.crypto.decryptPubSub(args[0])

                    update = MessageReader(xmessage)
                    length = update.readUint32BE()

                    got_bytes = update.getRemainingData()
                    try:
                        unzipped = zlib.decompress(got_bytes)
                    except OSError as e:
                        LOG.error(e)
                    except:
                        LOG.error('error zlib.decompress ', sys.exc_info()[0])
                    else:
                        if len(unzipped) != length:
                            LOG.info(
                                "Unexpected uncompressed data length, have=" + str(len(unzipped)) + ", expected=" + str(
                                    length))
                        args[0] = unzipped.decode('utf-8')
        else:
            if msg['pubsub_event']['items']['item']['update']['data'] is not None:
                args = data2py(msg['pubsub_event']['items']['item']['update'])

        # arg contains the devices that changed
        if args:
            await self.update_devices(args[0])

    async def update_devices(self, xml):
        root = ET.fromstring(xml)

        updated_devices = set()

        # Iterate over all channels -> devices -> datapoints
        devices = root.find('devices')
        for device in devices.findall('device'):
            serialnumber = device.get('serialNumber')

            channels = device.find('channels')
            if channels is not None:
                for channel in channels.findall('channel'):
                    channel_id = channel.get('i')

                    datapoints = device.findall('.//dataPoint')
                    if datapoints is not None:
                        for datapoint in datapoints:
                            datapoint_id = datapoint.get('i')

                            # Notify every device that monitors the received datapoint
                            lookup_key = serialnumber + '/' + channel_id + '/' + datapoint_id
                            value = datapoint.find('value')
                            if lookup_key in self.monitored_datapoints and value is not None:
                                monitoring_device = self.monitored_datapoints[lookup_key]
                                LOG.info("device %s: sending updated datapoint %s = %s", monitoring_device.name, lookup_key, value.text)
                                monitoring_device.update_datapoint(datapoint_id, value.text)
                                updated_devices.add(monitoring_device)

        for device in updated_devices:
            await device.after_update()


    def update_binary(self, device_id, channel):
        """ Update the status of binary devices   """
        LOG.info("binary info channel %s device %s in/output %s ", channel , device_id, self.binary_devices[device_id].output_device)
        # normally it is a output device, but if it is not linked, then it has a input datapoint
        if self.binary_devices[device_id].output_device[0] == 'o':           
            binary_state = get_output_datapoint(channel, self.binary_devices[device_id].output_device)
        else:
            binary_state = get_input_datapoint(channel, self.binary_devices[device_id].output_device)
        if binary_state is not None:
            self.binary_devices[device_id].state = binary_state
            LOG.info("binary device %s output %s is %s", device_id, self.binary_devices[device_id].output_device, binary_state)

    def update_sensor(self, device_id, channel):
        sensor_state = get_output_datapoint(channel, self.sensor_devices[device_id].output_device)
        if sensor_state is not None:
            self.sensor_devices[device_id].state = sensor_state
            LOG.info("sensor device %s output %s is %s", device_id, self.sensor_devices[device_id].output_device, sensor_state)    

    def update_lock(self, device_id, channel):
        lock_state = get_output_datapoint(channel, 'odp0000')
        if lock_state is not None:
            self.lock_devices[device_id].state = lock_state
            LOG.info("lock device %s output %s is %s", device_id, lock_state)            

    def add_device(self, fah_class, channel, channel_id, display_name, device_info, serialnumber, pairing_ids):
        """ Add generic device to the list of light devices   """
        datapoints = get_datapoints_by_pairing_ids(channel, pairing_ids)

        device = fah_class(
                self,
                device_info,
                serialnumber,
                channel_id,
                display_name,
                datapoints=datapoints)

        lookup_key = serialnumber + '/' + channel_id
        self.devices[lookup_key] = device

        for datapoint in datapoints.values():
            self.monitored_datapoints[serialnumber + '/' + channel_id + '/' + datapoint] = device

        LOG.info('light  %s %s, datapoints %s', lookup_key, display_name, datapoints)


    def add_dimmer_device(self, channel, channel_id, display_name, device_info, serialnumber):
        """ Add a dimmer unit to the list of light devices  """
        brightness = get_output_datapoint(channel, 'odp0001')
        light_state = (get_output_datapoint(channel, 'odp0000') == '1')

        lookup_key = serialnumber + '/' + channel_id
        self.light_devices[lookup_key] = FahLight(self, device_info, serialnumber, channel_id, display_name,
                                                    light_state, light_type='dimmer',
                                                    brightness=brightness)

        LOG.info('dimmer %s %s is %s', lookup_key, display_name, light_state)


    def add_scene(self, channel, channel_id, display_name, device_info, serialnumber):
        """ Add a scene to the list of scenes   """
        lookup_key = serialnumber + '/' + channel_id
        self.scene_devices[lookup_key] = FahLightScene(self, device_info, serialnumber, channel_id, display_name)

        LOG.info('scene  %s %s', lookup_key, display_name)


    def add_sensor_unit(self, channel, channel_id, display_name, device_info, serialnumber):
        """ Add a sensor unit to the list of binary devices """
        state = get_output_datapoint(channel, 'odp0000')
        lookup_key = serialnumber + '/' + channel_id

        self.binary_devices[lookup_key] = FahBinarySensor(self, device_info, serialnumber, channel_id, display_name, state=state)

        LOG.info('binary button %s %s is %s', lookup_key, display_name, state)


    def add_binary_sensor(self, xmlroot, device_info, serialnumber, roomnames):
        """ Add a binary sensor to the list of binary devices   """
        channels = xmlroot.find('channels')
        if channels is not None:
            for channel in channels.findall('channel'):
                channel_id = channel.get('i')

                floor_id = get_attribute(channel, 'floor')
                room_id = get_attribute(channel, 'room')
                function_id = get_attribute(channel, 'functionId')
                outputid = 'odp000' + self.binary_function_output[function_id] 

                binary_state = get_output_datapoint(channel, outputid )

                binary_device = serialnumber + '/' + channel_id
                binary_name = 'binary-' + channel_id
                if floor_id != '' and room_id != '' and self.use_room_names:
                    binary_name = binary_name + ' (' + roomnames[floor_id][room_id] + ')'
                self.binary_devices[binary_device] = FahBinarySensor(self, device_info, serialnumber, channel_id,
                                                                     binary_name, state=binary_state, output_device=outputid)

                LOG.info('binary %s %s output %s is %s', binary_device, binary_name, outputid , binary_state)

    def add_movement_detector(self, xmlroot, device_info, serialnumber, roomnames):
        ''' Add a movement detector to the list of binary devices '''

        movement_basename = get_attribute(xmlroot, 'displayName')
        floor_id = get_attribute(xmlroot, 'floor')
        room_id = get_attribute(xmlroot, 'room')

        if floor_id != '' and room_id != '' and self.use_room_names:
            movement_name = movement_basename + ' (' + roomnames[floor_id][room_id] + ')'
        else:
            movement_name = movement_basename
            
        channels = xmlroot.find('channels')
        if channels is not None:
            for channel in channels.findall('channel'):
                channel_id = channel.get('i')

                outputid = 'odp0000' 
                movement_device = serialnumber + '/' + channel_id
        else:
            channel_id = 'ch0000'
            outputid = 'idp0000'
            movement_device = serialnumber + '/' + channel_id
            
        self.binary_devices[movement_device] = FahBinarySensor(self, device_info, serialnumber, channel_id, movement_name, output_device=outputid)

        """ a movement detector als has a lux sensor """
        channel_id = 'ch0000'
        outputid = 'odp0002'
        movement_device = serialnumber + '/' + channel_id
        station_name = movement_name + '_lux'                     
        self.sensor_devices[movement_device] = FahSensor(self, device_info, serialnumber, channel_id, station_name, 'lux', '0', outputid)

        LOG.info('movement sensor %s %s ', movement_device, movement_name)

		
    def add_weather_station(self, xmlroot, device_info, serialnumber):
        ''' The weather station consists of 4 different sensors '''
        station_basename = get_attribute(xmlroot, 'displayName')

        channels = xmlroot.find('channels')
        if channels is not None:        
           for channel in channels.findall('channel'):
                channel_id = channel.get('i')
                function_id = get_attribute(channel, 'functionId')

                sensor_device = serialnumber + '/' + channel_id
          
                outputid = self.weatherstation_function_output[function_id]    
                state = get_output_datapoint(channel, outputid)

                # Luxsensor
                if function_id == '41': 
                    station_name = station_basename + '_lux'                     
                    self.sensor_devices[sensor_device] = FahSensor(self, device_info, serialnumber, channel_id, station_name, 'lux', state, outputid)

                # Rainsensor
                if function_id == '42':
                    station_name = station_basename + '_rain'
                    self.sensor_devices[sensor_device] = FahSensor(self, device_info, serialnumber, channel_id, station_name, 'rain', state, outputid)

                # Temperaturesensor
                if function_id == '43':
                    station_name = station_basename + '_temperature'
                    self.sensor_devices[sensor_device] = FahSensor(self, device_info, serialnumber, channel_id, station_name, 'temperature', state, outputid)

                # Windsensor
                if function_id == '44':
                    station_name = station_basename + '_windstrength'
                    self.sensor_devices[sensor_device] = FahSensor(self, device_info, serialnumber, channel_id, station_name, 'windstrength', state, outputid)
              
    def scan_panel(self, xmlroot, device_info, serialnumber, roomnames):

        channels = xmlroot.find('channels')
        if channels is not None:             
            for channel in channels.findall('channel'):
                channel_id = channel.get('i')
                function_id = get_attribute(channel, 'functionId')

                lock_device = serialnumber + '/' + channel_id

                # FID_DoorOpenerActuator
                if function_id == '1a':                                  
                    lock_name = get_attribute(channel, 'displayName')
                    floor_id = get_attribute(channel, 'floor')
                    room_id = get_attribute(channel, 'room')

                    lock_state = get_output_datapoint(channel, 'odp0000')

                    if lock_name == '':
                        lock_name = lock_device
                    if floor_id != '' and room_id != '' and self.use_room_names:
                        lock_name = lock_name + ' (' + roomnames[floor_id][room_id] + ')'

                    self.lock_devices[lock_device] = FahLock(self, device_info, serialnumber, channel_id, lock_name, lock_state)

                    LOG.info('lock  %s %s is %s', lock_device, lock_name, lock_state)

    async def get_config(self):
        """Get config file via getAll RPC"""
        my_iq = await self.send_rpc_iq('RemoteInterface.getAll', 'de', 2, 0, 0)
        my_iq.enable('rpc_query')

        if my_iq['rpc_query']['method_response']['fault'] is not None:
            fault = my_iq['rpc_query']['method_response']['fault']
            LOG.info(fault['string'])
            return None

        args = xml2py(my_iq['rpc_query']['method_response']['params'])
        return args[0]


    async def find_devices(self, use_room_names):
        """ Find the devices in the system, this is a big XML file   """
        self.use_room_names = use_room_names
        config = await self.get_config()

        if config is not None:
            self.found_devices = True

            root = ET.fromstring(config)

            # make a list of the rooms and other names
            roomnames = get_room_names(root)
            names = get_names(root)

            # Now look for the devices
            devices = root.find('devices')

            for device in devices.findall('device'):
                device_serialnumber = device.get('serialNumber')
                device_id = device.get('deviceId')
                device_name_id = device.get('nameId')
                device_sw_version = device.get('softwareVersion')

                device_display_name = get_attribute(device, 'displayName')
                device_floor_id = get_attribute(device, 'floor')
                device_room_id = get_attribute(device, 'room')
                device_model = names[device_name_id]

                device_name = device_display_name if device_display_name != '' else device_model
                device_name = device_name + " (" + device_serialnumber + ")"

                # Ignore devices from external integrations (i.e. Hue)
                is_external = device.get('isExternal')
                if is_external == 'true':
                    LOG.info('Ignoring device with serialnumber %s since it is external', device_serialnumber)
                    continue

                # Ignore devices that are not yet commissioned
                state = device.get('commissioningState')
                if state != 'ready':
                    LOG.info('Ignoring device with serialnumber %s since its commissioning state is not ready', device_serialnumber)
                    continue

                channels = device.find('channels');

                # Ignore devices without channels
                if channels is None:
                    LOG.info('Ignoring device with serialnumber %s since has no channels', device_serialnumber)
                    continue

                device_info = {"identifiers": {("freeathome", device_serialnumber)}, "name": device_name, "model": device_model, "sw_version": device_sw_version}

                for channel in channels.findall('channel'):
                    channel_id = channel.get('i')
                    channel_name_id = int(channel.get('nameId'), 16)
                    function_id = get_attribute(channel, 'functionId')
                    function_id = int(function_id, 16) if (function_id is not None and function_id != '') else None

                    same_location = channel.get('sameLocation')
                    channel_display_name = get_attribute(channel, 'displayName')
                    channel_floor_id = get_attribute(channel, 'floor')
                    channel_room_id = get_attribute(channel, 'room')

                    # Use room information from device if channel is in same location
                    floor_id = device_floor_id if channel_floor_id == '' or same_location == 'true' else channel_floor_id
                    room_id = device_room_id if channel_floor_id == '' or same_location == 'true' else channel_room_id

                    # Use device display name if not configured on channel
                    display_name = channel_display_name if channel_display_name != '' else device_display_name

                    # Use serial number and channel if no name is configured
                    if display_name == '':
                        display_name = device_serialnumber + '/' + channel_id

                    # Add room name to display name if user wishes so
                    room_suffix = ''
                    if floor_id != '' and room_id != '' and self.use_room_names:
                        room_suffix = ' (' + roomnames[floor_id][room_id] + ')'

                    if room_id == '':
                        LOG.info('Ignoring serialnumber %s, channel_id %s, function ID %s since it is not assigned to a room', device_serialnumber, channel_id, function_id)
                        continue

                    LOG.info('Encountered serialnumber %s, channel_id %s, function ID %s', device_serialnumber, channel_id, function_id)

                    # Switch actuators
                    if function_id in FUNCTION_IDS_SWITCHING_ACTUATOR:
                        pairing_ids = FahLight.pairing_ids()
                        self.add_device(FahLight, channel, channel_id, display_name + room_suffix, device_info, device_serialnumber, pairing_ids=pairing_ids)

                    # # Dimming actuators
                    # if function_id in FUNCTION_IDS_DIMMING_ACTUATOR:
                    #     self.add_dimmer_device(channel, channel_id, display_name + room_suffix, device_info, device_serialnumber)

                    # # Scene or Timer
                    # if function_id in FUNCTION_IDS_SCENE:
                    #     self.add_scene(channel, channel_id, display_name + room_suffix, device_info, device_serialnumber)

                    # blind/cover device
                    if function_id in FUNCTION_IDS_BLIND_ACTUATOR:
                        pairing_ids = FahCover.pairing_ids()
                        self.add_device(FahCover, channel, channel_id, display_name + room_suffix, device_info, device_serialnumber, pairing_ids=pairing_ids)

                    # # Sensor units 1/2 way
                    # if function_id in FUNCTION_IDS_SENSOR_UNIT:
                    #     # Do not add sensor unit if it is not assigned to a device
                    #     if not is_output_datapoint_assigned(channel, 'odp0000'):
                    #         LOG.info('Ignoring serialnumber %s, channel_id %s, function ID %s since it has no address assigned', device_serialnumber, channel_id, function_id)
                    #         continue

                    #     # Add position suffix to name, e.g. 'LT' for left, top
                    #     position_suffix = NAME_IDS_TO_BINARY_SENSOR_SUFFIX[channel_name_id] if channel_display_name == '' else ''

                    #     self.add_sensor_unit(channel, channel_id, display_name + position_suffix + room_suffix, device_info, device_serialnumber)


                    # thermostat
                    if function_id in FUNCTION_IDS_ROOM_TEMPERATURE_CONTROLLER:
                        pairing_ids = FahThermostat.pairing_ids()
                        self.add_device(FahThermostat, channel, channel_id, display_name + room_suffix, device_info, device_serialnumber, pairing_ids=pairing_ids)

                    # TODO: Add binary sensor based on its function ID
                    # # binary sensor
                    # if device_id == 'B005' or device_id == 'B006' or device_id == 'B007':
                    #     self.add_binary_sensor(device, device_info, device_serialnumber, roomnames)

                    # TODO: Add movement and lux sensor based on their function IDs
                    # # movement detector
                    # if device_id == '100A' or device_id == '9008' or device_id == '900A' or \
                    #    device_id == '1008':
                    #     self.add_movement_detector(device, device_info, device_serialnumber, roomnames)

                    # TODO: Add sensors one by one, based on their function ID
                    # # weather station
                    # if device_id == '101D':
                    #     self.add_weather_station(device, device_info, device_serialnumber)

                    # TODO: Add lock based on function id
                    # # 7 inch panel with possible lock controll
                    # if device_id == '1038':
                    #     self.scan_panel(device, device_info, device_serialnumber, roomnames)



            # Update all devices with initial state
            await self.update_devices(config)

class FreeAtHomeSysApp(object):
    """"  This class connects to the Busch Jeager Free @ Home sysapp
          parameters in configuration.yaml
          host       - Ip adress of the sysapp device
          username
          password
          use_room_names - Show room names with the devices
    """

    def __init__(self, host, user, password):
        """ x   """
        self._host = host
        self._port = 5222
        self._user = user
        self._jid = None
        self._password = password
        self.xmpp = None
        self._use_room_names = False
        self.reconnect = True

    @property
    def use_room_names(self):
        """ getter use_room_names   """
        return self._use_room_names

    @use_room_names.setter
    def use_room_names(self, value):
        """ setter user_room_names   """
        self._use_room_names = value

    async def connect(self):
        """ connect to the Free@Home sysap   """
        settings = SettingsFah(self._host)
        await settings.load_json()
        self._jid = settings.get_jid(self._user)

        iterations = None
        salt = None
        self.xmpp = None

        LOG.info('Connect Free@Home  %s ', self._jid)

        if self._jid is not None:
            fahversion = settings.get_flag('version')

            if version.parse(fahversion) >= version.parse("2.3.0"):
                iterations, salt = settings.get_scram_settings(self._user, 'SCRAM-SHA-256')
            # create xmpp client
            self.xmpp = Client(self._jid, self._password, self._host, self._port, fahversion, iterations, salt, self.reconnect)
            # connect
            self.xmpp.sysap_connect()

    async def disconnect(self):
        """Disconnect from sysap."""
        if self.xmpp is not None:
            # Make sure that client does not reconnect
            self.xmpp.reconnect = False
            self.xmpp.disconnect()

        return True


    async def wait_for_connection(self):
        """ Wait til connection is made, if failed at first attempt retry until success """
        if self.xmpp is not None:
            while self.xmpp.connect_ready() is False and self.xmpp.connecting_in_error() is False:
                LOG.info('waiting for connection')
                await asyncio.sleep(1)
            if self.xmpp.connect_in_error is True:
                return False
            else:
                return True

    def get_devices(self, device_type):
        """ Get devices of a specific type from the sysap   """
        return self.xmpp.get_devices(device_type)

    async def find_devices(self):
        """ find all the devices on the sysap   """
        try:
            await self.xmpp.find_devices(self._use_room_names)
        except IqError as error:
            raise error
