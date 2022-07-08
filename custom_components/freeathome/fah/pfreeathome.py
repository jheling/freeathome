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
import re
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

from .devices.fah_light import FahLight
from .devices.fah_binary_sensor import FahBinarySensor
from .devices.fah_thermostat import FahThermostat
from .devices.fah_light_scene import FahLightScene
from .devices.fah_cover import FahCover
from .devices.fah_sensor import FahSensor
from .devices.fah_lock import FahLock

from .const import (
    NAME_IDS_TO_BINARY_SENSOR_SUFFIX,
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


def is_output_pairing_id_assigned(xmlnode, pairing_id):
    """Return True if output datapoint has an address assigned"""
    outputs = xmlnode.find('outputs')
    for datapoint in outputs.findall('dataPoint'):
        if int(datapoint.get('pairingId'), 16) == pairing_id:
            if datapoint.find('address') is not None:
                return True
    return False


def get_datapoint_by_pairing_id(xmlnode, type, pairing_id):
    """Returns output datapoint by pairing id."""
    for datapoint in xmlnode.find(type).findall('dataPoint'):
        if int(datapoint.get('pairingId'), 16) == pairing_id:
            return datapoint.get('i')

    return None


def get_parameter_by_parameter_id(xmlnode, type, parameter_id):
    """Returns output parameter by parameter id."""
    for parameter in xmlnode.find(type).findall('parameter'):
        if int(parameter.get('parameterId'), 16) == parameter_id:
            return parameter.get('i')

    return None


def get_datapoints_by_pairing_ids(xmlnode, pairing_ids):
    """Returns a dict with pairing id as key and datapoint number as value."""
    datapoints = {}
    for type, pairing_ids_for_type in pairing_ids.items():
        for pairing_id in pairing_ids_for_type:
            dp = get_datapoint_by_pairing_id(xmlnode, type, pairing_id)
            if dp is not None:
                datapoints[pairing_id] = dp

    return datapoints


def get_parameters_by_parameter_ids(xmlnode, parameter_ids):
    """Returns a dict with parameter id as key and parameter number as value."""
    parameters = {}
    for type, parameter_ids_for_type in parameter_ids.items():
        for parameter_id in parameter_ids_for_type:
            param = get_parameter_by_parameter_id(xmlnode, type, parameter_id)
            if param is not None:
                parameters[parameter_id] = param

    return parameters


def get_all_datapoints_as_str(xmlnode):
    """Returns all datapoints."""
    datapoints = []
    for datapoint in xmlnode.findall('.//dataPoint'):
        dp = datapoint.get('i')
        pid = datapoint.get('pairingId')
        pid_10 = int(pid, 16)
        nameid = datapoint.get('nameId')
        datapoints.append("dp %s pid 0x%s/%s nameid %s" % (dp, pid, pid_10, nameid))

    return datapoints


class Client(slixmpp.ClientXMPP):
    """ Client for connecting to the free@home sysap   """
    found_devices = False
    connect_finished = False
    authenticated = False
    use_room_names = False
    connect_in_error = False

    # The specific devices
    devices = set()
    monitored_datapoints = {}
    monitored_parameters = {}

    _update_handlers = []

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
            self.saslhandler = SaslHandler(self, self.x_jid, self.password, self.iterations, self.salt)

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
        LOG.warn("Connection with SysAP lost")
        self.connect_in_error = True
        if not self.reconnect:
            return

        await asyncio.sleep(2)

        if version.parse(self.fahversion) >= version.parse("2.3.0"):
            self.saslhandler = SaslHandler(self, self.x_jid, self.password, self.iterations, self.salt)

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

        self['xep_0030'].static.add_identity(self.boundjid, capsversion, '', identity)
        self['xep_0030'].static.set_features(self.boundjid, capsversion, '', features)

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

    async def set_parameter(self, serialnumber, channel_id, parameter, command):
        """ Send a command to the sysap   """
        LOG.info("set_parameter %s/%s %s %s", serialnumber, channel_id, parameter, command)

        name = serialnumber + '/' + channel_id + '/' + parameter

        try:
            await self.send_rpc_iq('RemoteInterface.setParameter',
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
        return [el for el in self.devices if isinstance(el, device_class)]

    def get_devices(self, device_type):
        """ After all the devices have been extracted from the xml file,
        the lists with device objects are returned to HA
        """
        return_type = {}

        if device_type == 'light':
            return self.filter_devices(FahLight)

        if device_type == 'scene':
            return self.filter_devices(FahLightScene)

        if device_type == 'cover':
            return self.filter_devices(FahCover)

        if device_type == 'binary_sensor':
            return self.filter_devices(FahBinarySensor)

        if device_type == 'thermostat':
            return self.filter_devices(FahThermostat)

        if device_type == 'sensor':
            return self.filter_devices(FahSensor)

        if device_type == 'lock':
            return self.filter_devices(FahLock)

        return return_type

    def roster_callback(self, roster_iq):
        """ If the roster callback is called, the initial connection has finished  """
        LOG.debug("Roster callback ")
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

    async def update_devices(self, xml, initializing=False):
        """Parse received update XML and update devices."""
        # Notify update handlers
        for handler in self._update_handlers:
            handler(xml)

        # Ugly hack: Some SysAPs seem to return invalid XML, i.e. duplicate name attributes
        # Strip them altogether.
        xml_without_names = re.sub(r'name="[^"]*" ([^>]*)name="[^"]*"', r'\1', xml)

        root = ET.fromstring(xml_without_names)

        updated_devices = set()

        # Iterate over all channels -> devices -> datapoints
        devices = root.find('devices')
        for device in devices.findall('device'):
            serialnumber = device.get('serialNumber')

            channels = device.find('channels')
            if channels is not None:
                for channel in channels.findall('channel'):
                    channel_id = channel.get('i')

                    # Check if channel has a <function> key. If so, get the current functions sensorMatchCode
                    # and actuatorMatchCode, which serve as a filter for relevant datapoints
                    # This ist mostly useful to correctly set the initial state for binary sensors
                    datapoint_filter_mask = 0xFFFFFFFF

                    xml_function_id = channel.find("attribute[@name='functionId']")
                    if xml_function_id is not None:

                        # Lookup function ID in list of all possible function IDs for this channel
                        function_id = int(xml_function_id.text, 16)
                        xml_function = channel.find("functions/function[@functionId='%04x']" % function_id)

                        if xml_function is not None:
                            # Get sensor and actuator match codes and combine both to act as a datapoint filter
                            sensor_match_code = int(xml_function.get("sensorMatchCode"), 16)
                            actuator_match_code = int(xml_function.get("actuatorMatchCode"), 16)
                            datapoint_filter_mask = sensor_match_code | actuator_match_code

                    datapoints = channel.findall('.//dataPoint') # All available dataPoints
                    parameters = channel.findall('.//parameter') # All available parameters

                    # Update datapoints
                    if datapoints is not None:
                        for datapoint in datapoints:

                            # If match code is present (i.e. initializing), check if match code matches filter
                            match_code_hex = datapoint.get("matchCode")
                            if match_code_hex is not None:
                                match_code = int(match_code_hex, 16)
                                if match_code & datapoint_filter_mask == 0:
                                    continue

                            datapoint_id = datapoint.get('i')

                            # Notify every device that monitors the received datapoint
                            lookup_key = serialnumber + '/' + channel_id + '/' + datapoint_id
                            value = datapoint.find('value')

                            # Do not spam log messages during initialization, or if value is None
                            if not initializing and value is not None:
                                LOG.debug("received datapoint %s = %s", lookup_key, value.text)

                            if lookup_key in self.monitored_datapoints and value is not None:
                                monitoring_device = self.monitored_datapoints[lookup_key]
                                LOG.debug("%s %s: received datapoint %s = %s", monitoring_device.__class__.__name__, monitoring_device.name, lookup_key, value.text)
                                monitoring_device.update_datapoint(datapoint_id, value.text)
                                updated_devices.add(monitoring_device)

                    # Update parameters
                    if parameters is not None:
                        for parameter in parameters:

                            # TODO: Do we require matchCode stuff?
                            parameter_id = parameter.get('i')

                             # Notify every device that monitors the received datapoint
                            lookup_key = serialnumber + '/' + channel_id + '/' + parameter_id
                            value = parameter.find('value')

                            # Do not spam log messages during initialization, or if value is None
                            if not initializing and value is not None:
                                LOG.debug("received parameter %s = %s", lookup_key, value.text)

                            if lookup_key in self.monitored_parameters and value is not None:
                                monitoring_device = self.monitored_parameters[lookup_key]
                                LOG.debug("%s %s: received parameter %s = %s", monitoring_device.__class__.__name__, monitoring_device.name, lookup_key, value.text)
                                monitoring_device.update_parameter(parameter_id, value.text)
                                updated_devices.add(monitoring_device)


        for device in updated_devices:
            await device.after_update()

    def add_update_handler(self, handler):
        """Add update handler"""
        self._update_handlers.append(handler)

    def clear_update_handlers(self):
        """Clear update handlers"""
        self._update_handlers = []


    def add_device(self, fah_class, channel, channel_id, display_name, device_info, serialnumber, datapoints, parameters):
        """ Add generic device to the list of light devices   """
        device = fah_class(
                self,
                device_info,
                serialnumber,
                channel_id,
                display_name,
                datapoints=datapoints,
                parameters=parameters)

        lookup_key = serialnumber + '/' + channel_id
        self.devices.add(device)

        for datapoint in datapoints.values():
            # State of devices is published only through output datapoints, so do not listen for input datapoints.
            # There may be a better way to check for this.
            if datapoint is None or datapoint[0] == 'i':
                continue
            LOG.debug('Monitoring datapoint ' + serialnumber + '/' + channel_id + '/' + datapoint)
            self.monitored_datapoints[serialnumber + '/' + channel_id + '/' + datapoint] = device

        for parameter in parameters.values():
            if parameter is None or parameter[0] == 'i':
                continue
            LOG.debug('Monitoring parameter ' + serialnumber + '/' + channel_id + '/' + parameter)
            self.monitored_parameters[serialnumber + '/' + channel_id + '/' + parameter] = device

        LOG.info('add device %s  %s %s, datapoints %s, parameters %s', fah_class.__name__, lookup_key, display_name, datapoints, parameters)


    async def get_config(self, pretty=False):
        """Get config file via getAll RPC"""
        pretty_value = 1 if pretty else 0
        my_iq = await self.send_rpc_iq('RemoteInterface.getAll', 'de', 2, pretty_value, 0)
        my_iq.enable('rpc_query')

        if my_iq['rpc_query']['method_response']['fault'] is not None:
            fault = my_iq['rpc_query']['method_response']['fault']
            LOG.info(fault['string'])
            return None

        args = xml2py(my_iq['rpc_query']['method_response']['params'])
        return args[0]

    async def get_all_xml(self):
        config = await self.get_config()

        if config is None:
            return None
        
        return re.sub(r'name="[^"]*" ([^>]*)name="[^"]*"', r'\1', config)


    async def find_devices(self, use_room_names):
        """ Find the devices in the system, this is a big XML file   """
        self.use_room_names = use_room_names
        config = await self.get_config()

        if config is not None:
            self.found_devices = True

            # Ugly hack: Some SysAPs seem to return invalid XML, i.e. duplicate name attributes
            # Strip them altogether.
            config_without_names = re.sub(r'name="[^"]*" ([^>]*)name="[^"]*"', r'\1', config)

            root = ET.fromstring(config_without_names)

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

                LOG.info('Device: device id %s, name id %s, serialnumber %s, display name %s', device_id, device_name_id, device_serialnumber, device_display_name)

                # TODO: Move this to the home assistant component and make it user configurable
                # (Default should be false, to avoid circular definitions for users with
                # emulated_hue enabled
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

                channels_xml = device.find('channels')

                # Ignore devices without channels
                if channels_xml is None:
                    LOG.info('Ignoring device with serialnumber %s since has no channels', device_serialnumber)
                    continue

                # There may be a device-level parameter called deviceChannelSelector. Each possible value of that
                # parameter has a mask attribute. This mask can be used to filter applicable channelSelectors,
                # see below.
                device_filter_mask = 0xFFFFFFFF
                device_channel_selector_parameter = device.find("./parameters/parameter[@deviceChannelSelector='true']")
                if device_channel_selector_parameter is not None:
                    parameter_value = device_channel_selector_parameter.find("value").text
                    device_filter_mask = int(parameter_value, 16) # e.g. '00000001' -> 0x00000001

                # Filter channels based on channelSelector
                # There is a device-level parameter called channelSelector. Each possible value of that parameter
                # has a mask attribute. This mask can be used to filter channels that should be active.
                # E.g. consider a sensor unit 1-gang. The sensor unit has two modes:
                # 1. Rocker (aka on/off): mask 00000001
                # 2. Push button: mask 00000002
                # The sensor unit has three channels:
                # 1. ch0000 (On/off): mask 00000001
                # 2. ch0001 (Push button top): mask 00000002
                # 3. ch0002 (Push button bottom: mask 00000002
                # --> In Rocker mode, ch0000 is active, in Push button mode ch0001 and ch0002 is active
                filter_mask = 0xFFFFFFFF
                channel_selector_parameters = device.findall("./parameters/parameter[@channelSelector='true']")
                for channel_selector_parameter in channel_selector_parameters:
                    # Check if matchCode matches deviceChannelSelector (see above)
                    parameter_mask = int(channel_selector_parameter.get("matchCode"), 16)
                    if parameter_mask & device_filter_mask:
                        # See which option user has selected, e.g. '1'
                        parameter_value = channel_selector_parameter.find("value").text
                        # Find that option in the list of options
                        option = channel_selector_parameter.find("./valueEnum/option[@key='{}']".format(parameter_value))
                        # Get filter mask from mask attribute
                        filter_mask = int(option.get('mask'), 16) # e.g. '00000001' -> 0x00000001

                device_info = {
                        "configuration_url": "http://{}/".format(self._host),
                        "identifiers": {("freeathome", device_serialnumber)},
                        "name": device_name,
                        "model": device_model,
                        "sw_version": device_sw_version,
                        }

                for channel in channels_xml.findall('channel'):
                    channel_id = channel.get('i')
                    channel_name_id = int(channel.get('nameId'), 16)
                    function_id = get_attribute(channel, 'functionId')
                    function_id = int(function_id, 16) if (function_id is not None and function_id != '') else None

                    # Check if channel matches filter mask
                    channel_mask = int(channel.get("mask"), 16)
                    if not channel_mask & filter_mask:
                        LOG.info('Ignoring serialnumber %s, channel_id %s, function ID %s since its channel mask %08x does not match device filter mask %08x', device_serialnumber, channel_id, function_id, channel_mask, filter_mask)
                        continue

                    same_location = channel.get('sameLocation')
                    channel_display_name = get_attribute(channel, 'displayName')
                    channel_floor_id = get_attribute(channel, 'floor')
                    channel_room_id = get_attribute(channel, 'room')

                    # TODO: Move this to the custom component part
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
                    LOG.debug(get_all_datapoints_as_str(channel))

                    # Ask all classes if the current function ID should be handled
                    for fah_class in [FahLight, FahCover, FahBinarySensor, FahThermostat, FahLightScene, FahSensor, FahLock]:
                        # Add position suffix to name, e.g. 'LT' for left, top
                        position_suffix = NAME_IDS_TO_BINARY_SENSOR_SUFFIX.get(channel_name_id, '')

                        # If function should be handled, it returns a list of relevant pairing IDs
                        pairing_ids = fah_class.pairing_ids(function_id)

                        # List of pairing IDs was returned, so given class wants to handle the current
                        # function with the returned pairing IDs.
                        if pairing_ids is not None:
                            datapoints = get_datapoints_by_pairing_ids(channel, pairing_ids)

                            # Create an empty for all non thermostat devices
                            parameters = {}

                            # TODO: Get parameters for all device types
                            if(fah_class in  [FahThermostat]):
                                parameter_ids = fah_class.parameter_ids(function_id)
                                parameters = get_parameters_by_parameter_ids(channel,parameter_ids)

                            # There is at least one matching datapoint for requested pairing IDs, so
                            # add the device
                            if not all(value is None for value in datapoints.values()):
                                self.add_device(fah_class, channel, channel_id, display_name + position_suffix + room_suffix, device_info, device_serialnumber, datapoints=datapoints, parameters = parameters)


            # Update all devices with initial state
            await self.update_devices(config, initializing=True)

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

    @property
    def host(self):
        """Getter for host"""
        return self._host

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

    async def get_all_xml(self):
        """ get the whole xml """
        try:
            xml = await self.xmpp.get_all_xml()
            return xml
        except IqError as error:
            raise error
    def get_raw_config(self, pretty=False):
        """Return raw config"""
        return self.xmpp.get_config(pretty=pretty)

    def add_update_handler(self, handler):
        """Add update handler"""
        self.xmpp.add_update_handler(handler)

    def clear_update_handlers(self):
        """Clear update handlers"""
        self.xmpp.clear_update_handlers()

    async def find_devices(self):
        """ find all the devices on the sysap   """
        try:
            await self.xmpp.find_devices(self._use_room_names)
        except IqError as error:
            raise error
