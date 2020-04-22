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
from .fah.messagereader import MessageReader
from .fah.settings import SettingsFah
from .fah.saslhandler import SaslHandler

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

    def __init__(self, client, device_id, name, device_updated_cb=None):
        self._device_id = device_id
        self._name = name
        self._client = client
        self._device_updated_cbs = []
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
    def device_id(self):
        """ return the unique device_id (combination deviceId and channel """
        return self._device_id

    @property
    def name(self):
        """ return the name of the device   """
        return self._name

    @property
    def client(self):
        """ return the Client object """
        return self._client


class FahBinarySensor(FahDevice):
    """Free@Home binary object """
    state = None
    output_device = None

    def __init__(self, client, device_id, name, state=False, output_device='odp0000'):
        FahDevice.__init__(self, client, device_id, name)
        self.state = state
        self.output_device = output_device

class FahThermostat(FahDevice):
    """Free@Home thermostat """
    current_temperature = None
    target_temperature = None

    def __init__(self, client, device_id, name, temperature=None, target=None, state=None, eco_mode=None):
        FahDevice.__init__(self, client, device_id, name)
        self.current_temperature = temperature
        self.target_temperature = target
        self.state = state
        self.ecomode = eco_mode

    async def turn_on(self):
        """ Turn the thermostat on   """
        await self.client.set_datapoint(self.device_id, 'idp0011', '0')
        await self.client.set_datapoint(self.device_id, 'idp0012', '1')

    async def turn_off(self):
        """ Turn the thermostat off   """
        await self.client.set_datapoint(self.device_id, 'idp0012', '0')

    async def eco_mode(self):
        """ Put the thermostat in eco mode   """
        await self.client.set_datapoint(self.device_id, 'idp0011', '2')

    async def set_target_temperature(self, temperature):
        await self.client.set_datapoint(self.device_id, 'idp0016', '%.2f' % temperature)

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


class FahLight(FahDevice):
    """ Free@Home light object   """
    state = None
    light_type = None
    brightness = None

    # pylint: disable=too-many-arguments
    def __init__(self, client, device_id, name, state=False, light_type='normal', brightness=None):
        FahDevice.__init__(self, client, device_id, name)
        self.state = state
        self.light_type = light_type
        self.brightness = brightness

    async def turn_on(self):
        """ Turn the light on   """
        oldstate = self.state
        await self.client.set_datapoint(self.device_id, 'idp0000', '1')
        self.state = True

        if self.light_type == 'dimmer' \
                and ((oldstate != self.state and int(self.brightness) > 0) or (oldstate == self.state)):
            await self.client.set_datapoint(self.device_id, 'idp0002', str(self.brightness))

    async def turn_off(self):
        """ Turn the light off   """
        await self.client.set_datapoint(self.device_id, 'idp0000', '0')
        self.state = False

    def set_brightness(self, brightness):
        """ Set the brightness of the light  """
        if self.light_type == 'dimmer':
            self.brightness = brightness

    def get_brightness(self):
        """ Return the brightness of the light  """
        return self.brightness

    def is_on(self):
        """ Return the state of the light   """
        return self.state


class FahLightScene(FahDevice):
    """ Free@home scene   """

    def __init__(self, client, device_id, name):
        FahDevice.__init__(self, client, device_id, name)

    async def activate(self):
        """ Activate the scene   """
        await self.client.set_datapoint(self.device_id, 'odp0000', '1')


class FahCover(FahDevice):
    """ Free@Home cover device
    In freeathome the value 100 indicates that the cover is fully closed
    In home assistant the value 100 indicates that the cover is fully open
    """
    state = None
    position = None

    # pylint: disable=too-many-arguments
    def __init__(self, client, device_id, name, state, position):
        FahDevice.__init__(self, client, device_id, name)
        self.state = state
        self.position = position

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

    async def set_cover_position(self, position):
        """ Set the cover position  """
        await self.client.set_datapoint(self.device_id, 'idp0002', str(abs(100 - position)))

    async def open_cover(self):
        """ Open the cover   """
        await self.client.set_datapoint(self.device_id, 'idp0000', '0')

    async def close_cover(self):
        """ Close the cover   """
        await self.client.set_datapoint(self.device_id, 'idp0000', '1')

    async def stop_cover(self):
        """ Stop the cover, only if it is moving """
        if (self.state == '2') or (self.state == '3'):
            await self.client.set_datapoint(self.device_id, 'idp0001', '1')


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


class Client(slixmpp.ClientXMPP):
    """ Client for connecting to the free@home sysap   """
    found_devices = False
    connect_finished = False
    authenticated = False
    use_room_names = False

    # The specific devices
    binary_devices = {}
    light_devices = {}
    scene_devices = {}
    cover_devices = {}
    thermostat_devices = {}

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
                
    def __init__(self, jid, password, fahversion, iterations=None, salt=None):
        """ x   """
        slixmpp.ClientXMPP.__init__(self, jid, password, sasl_mech='SCRAM-SHA-1')

        self.fahversion = fahversion
        self.x_jid = jid

        LOG.info(' version: %s', self.fahversion)

        if version.parse(self.fahversion) >= version.parse("2.3.0"):
            self.saslhandler = SaslHandler(self, jid, password, iterations, salt)

        import os
        import binascii
        self.requested_jid.resource = binascii.b2a_hex(os.urandom(4))

        # handle session_start and message events
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("roster_update", self.roster_callback)
        self.add_event_handler("pubsub_publish", self.pub_sub_callback)
        self.add_event_handler("failed_auth", self.failed_auth)
        
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

    async def set_datapoint(self, device, datapoint, command):
        """ Send a command to the sysap   """
        LOG.info("set_datapoint %s %s %s", device, datapoint, command)

        name = device + '/' + datapoint

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

    def get_devices(self, device_type):
        """ After all the devices have been extracted from the xml file,
        the lists with device objects are returned to HA
        """
        return_type = None

        if device_type == 'light':
            return_type = self.light_devices

        if device_type == 'scene':
            return_type = self.scene_devices

        if device_type == 'cover':
            return_type = self.cover_devices

        if device_type == 'binary_sensor':
            return_type = self.binary_devices

        if device_type == 'thermostat':
            return_type = self.thermostat_devices

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
            root = ET.fromstring(args[0])

            device = root.find('devices')
            for neighbor in device.findall('device'):
                serialnumber = neighbor.get('serialNumber')

                channels = neighbor.find('channels')
                if channels is not None:
                    for channel in channels.findall('channel'):
                        channel_id = channel.get('i')

                        # Now change the status of the device
                        device_id = serialnumber + '/' + channel_id

                        # if the device is a light
                        if device_id in self.light_devices:
                            self.update_light(device_id, channel)
                            await self.light_devices[device_id].after_update()

                        # if the device is a cover
                        if device_id in self.cover_devices:
                            self.update_cover(device_id, channel)
                            await self.cover_devices[device_id].after_update()

                        # if the device is a binary sensor
                        if device_id in self.binary_devices:
                            self.update_binary(device_id, channel)
                            await self.binary_devices[device_id].after_update()

                        # if the device is a thermostat
                        if device_id in self.thermostat_devices:
                            self.update_thermostat(device_id, channel)
                            await self.thermostat_devices[device_id].after_update()

    def update_light(self, device_id, channel):
        """ Update status of light devices   """
        light_state = get_output_datapoint(channel, 'odp0000')
        if light_state is not None:
            state = (light_state == '1')

            self.light_devices[device_id].state = state
            LOG.info("device %s (%s) is %s",
                     self.light_devices[device_id].name, device_id, state)

        brightness = get_output_datapoint(channel, 'odp0001')
        if brightness is not None:
            self.light_devices[device_id].brightness = brightness
            LOG.info("device %s (%s) brightness %s",
                     self.light_devices[device_id].name, device_id,
                     self.light_devices[device_id].brightness)

    def update_cover(self, device_id, channel):
        """ Update the status of blind/cover devices """
        cover_state = get_output_datapoint(channel, 'odp0000')
        if cover_state is not None:
            # 0 = open, 1 = closed , 2 = moving up, 3 = moving down
            self.cover_devices[device_id].state = cover_state
            LOG.info("device %s (%s) is %s",
                     self.cover_devices[device_id].name,
                     device_id, cover_state)
        cover_position = get_output_datapoint(channel, 'odp0001')
        if cover_position is not None:
            self.cover_devices[device_id].position = \
                str(abs(100 - int(float(cover_position))))

    def update_binary(self, device_id, channel):
        """ Update the status of binary devices   """
        LOG.info("binary info channel %s device %s output %s ", channel , device_id, self.binary_devices[device_id].output_device)
        binary_state = get_output_datapoint(channel, self.binary_devices[device_id].output_device)
        if binary_state is not None:
            self.binary_devices[device_id].state = binary_state
            LOG.info("binary device %s output %s is %s", device_id, self.binary_devices[device_id].output_device, binary_state)

    def update_thermostat(self, device_id, channel):
        """ Update the status of thermostat devices """
        target_temp_state = get_output_datapoint(channel, 'odp0006')
        if target_temp_state is not None:
            self.thermostat_devices[device_id].target_temperature = target_temp_state
            LOG.info("thermostat device %s target temp is %s", device_id, target_temp_state)

        state = get_output_datapoint(channel, 'odp0008')
        if state is not None:
            self.thermostat_devices[device_id].state = state
            LOG.info("thermostat device %s state is %s", device_id, state)

        eco_mode = get_output_datapoint(channel, 'odp0009')
        if eco_mode is not None:
            self.thermostat_devices[device_id].ecomode = eco_mode
            LOG.info("thermostat device %s eco mode is %s", device_id, eco_mode)

        current_temp_state = get_output_datapoint(channel, 'odp0010')
        if current_temp_state is not None:
            self.thermostat_devices[device_id].current_temperature = current_temp_state
            LOG.info("thermostat device %s current temp is %s", device_id, current_temp_state)

    def add_light_device(self, xmlroot, serialnumber, roomnames):
        """ Add a switch unit to the list of light devices   """
        channels = xmlroot.find('channels')

        if channels is not None:
            for channel in channels.findall('channel'):

                channel_id = channel.get('i')

                light_name = get_attribute(channel, 'displayName')
                floor_id = get_attribute(channel, 'floor')
                room_id = get_attribute(channel, 'room')

                light_state = (get_output_datapoint(channel, 'odp0000') == '1')

                single_light = serialnumber + '/' + channel_id
                if light_name == '':
                    light_name = single_light
                if floor_id != '' and room_id != '' and self.use_room_names:
                    light_name = light_name + ' (' + roomnames[floor_id][room_id] + ')'

                self.light_devices[single_light] = FahLight(self, single_light,
                                                            light_name, light_state)

                LOG.info('light  %s %s is %s', single_light, light_name, light_state)

    def add_dimmer_device(self, xmlroot, serialnumber, roomnames):
        """ Add a dimmer unit to the list of light devices  """
        channels = xmlroot.find('channels')

        if channels is not None:
            for channel in channels.findall('channel'):

                channel_id = channel.get('i')

                light_name = get_attribute(channel, 'displayName')
                floor_id = get_attribute(channel, 'floor')
                room_id = get_attribute(channel, 'room')

                brightness = get_output_datapoint(channel, 'odp0001')
                light_state = (get_output_datapoint(channel, 'odp0000') == '1')

                single_light = serialnumber + '/' + channel_id
                if light_name == '':
                    light_name = single_light
                if floor_id != '' and room_id != '' and self.use_room_names:
                    light_name = light_name + ' (' + roomnames[floor_id][room_id] + ')'
                self.light_devices[single_light] = FahLight(self, single_light, light_name,
                                                            light_state, light_type='dimmer',
                                                            brightness=brightness)

                LOG.info('dimmer %s %s is %s', single_light, light_name, light_state)

    def add_scene(self, xmlroot, serialnumber, roomnames):
        """ Add a scene to the list of scenes   """

        root_scene_name = get_attribute(xmlroot, 'displayName')
        root_floor_id = get_attribute(xmlroot, 'floor')
        root_room_id = get_attribute(xmlroot, 'room')

        channels = xmlroot.find('channels')

        if channels is not None:
            for channel in channels.findall('channel'):

                channel_id = channel.get('i')
                
                scene_name = get_attribute(channel, 'displayName')
                if scene_name == '':
                    scene_name = root_scene_name
                floor_id = get_attribute(channel, 'floor')
                if floor_id == '':
                    floor_id = root_floor_id                    
                room_id = get_attribute(channel, 'room')
                if room_id == '':
                    room_id = root_room_id
                    
                scene = serialnumber + '/' + channel_id
                if scene_name == '':
                    scene_name = scene

                if floor_id != '' and room_id != '' and self.use_room_names:
                    scene_name = scene_name + ' (' + roomnames[floor_id][room_id] + ')'

                self.scene_devices[scene] = FahLightScene(self, scene, scene_name)

                LOG.info('scene  %s %s', scene, scene_name)

    def add_cover_device(self, xmlroot, serialnumber, roomnames):
        """ Add a blind/cover to the list of cover devices   """
        channels = xmlroot.find('channels')

        if channels is not None:
            for channel in channels.findall('channel'):

                channel_id = channel.get('i')

                cover_name = get_attribute(channel, 'displayName')
                floor_id = get_attribute(channel, 'floor')
                room_id = get_attribute(channel, 'room')

                cover_state = get_output_datapoint(channel, 'odp0000')
                cover_position = str(abs(100 - int(float(get_output_datapoint(channel, 'odp0001')))))

                single_cover = serialnumber + '/' + channel_id
                if cover_name == '':
                    cover_name = single_cover
                if floor_id != '' and room_id != '' and self.use_room_names:
                    cover_name = cover_name + ' (' + roomnames[floor_id][room_id] + ')'
                self.cover_devices[single_cover] = FahCover(self, single_cover, cover_name,
                                                            cover_state, cover_position)

                LOG.info('cover %s %s is %s', single_cover, cover_name, cover_state)

    def add_sensor_unit(self, xmlroot, serialnumber, roomnames, device_id):

        """ Add a sensor unit to the list of binary devices
        A button has no channels, only parameters
        deviceid = 1002 - Double switch
          1 = left normal switch, right - normal switch (L, R)
          2 = left normal switch, right impulse switch (L, RU, RL)
          3 = left impulse switch, right switch (LU,LL, R)
          4 = left impulse , right impulse (LU,LL,RU,RL)
        device_id = 1000 - Single switch
          1 = Normal switch
          2 = Impulse switch
        The master message returns no initial state

        In the status message of a switch there are channels,
        left normal     right all impulse
        ---------       ---------
        | 0 | 3 |       | 1 | 4 |
        --------        ---------
        | 0 | 3 |       | 2 | 5 |
        ---------       ---------
        """

        button_list, button_type, position = None, None, None
        button_basename = get_attribute(xmlroot, 'displayName')
        floor_id = get_attribute(xmlroot, 'floor')
        room_id = get_attribute(xmlroot, 'room')

        parameters = xmlroot.find('parameters')
        parameter = parameters.find('parameter')
        value = parameter.find('value').text

        if device_id == '1000' or device_id == '100C':
            button_type = 1
            button_list = self.switch_type_1[value]

        if device_id == '1002' or device_id == '1019' or device_id == '1017':
            button_type = 2
            button_list = self.switch_type_2[value]

        for values in button_list:
            binary_device = serialnumber + '/ch000' + str(values)
            if button_type == 1:
                position = {0: '', 1: 'T', 2: 'B'}
            if button_type == 2:
                position = {0: 'L', 1: 'LT', 2: 'LB', 3: 'R', 4: 'RT', 5: 'RB'}
            button_name = button_basename + ' ' + position[values]
            if floor_id != '' and room_id != '' and self.use_room_names:
                button_name = button_name + ' (' + roomnames[floor_id][room_id] + ')'

            self.binary_devices[binary_device] = FahBinarySensor(self, binary_device, button_name)

            LOG.info('binary button %s %s ', binary_device, button_name)

    def add_binary_sensor(self, xmlroot, serialnumber, roomnames):
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
                self.binary_devices[binary_device] = FahBinarySensor(self, binary_device,
                                                                     binary_name, state=binary_state, output_device=outputid)

                LOG.info('binary %s %s output %s is %s', binary_device, binary_name, outputid , binary_state)

    def add_movement_detector(self, xmlroot, serialnumber, roomnames):
        ''' Add a movement detector to the list of binary devices '''
        channels = xmlroot.find('channels')
        if channels is not None:
            for channel in channels.findall('channel'):
                channel_id = channel.get('i')
                button_basename = get_attribute(xmlroot, 'displayName')
                floor_id = get_attribute(xmlroot, 'floor')
                room_id = get_attribute(xmlroot, 'room')

                button_device = serialnumber + '/' + channel_id
                if floor_id != '' and room_id != '' and self.use_room_names:
                    button_name = button_basename + ' (' + roomnames[floor_id][room_id] + ')'
                else:
                    button_name = button_basename
                self.binary_devices[button_device] = FahBinarySensor(self, button_device, button_name)
                LOG.info('movement sensor %s %s ', button_device, button_name)

    def add_thermostat(self, xmlroot, serialnumber, roomnames):
        """ Add a thermostat to the list of thermostat devices """
        button_basename = get_attribute(xmlroot, 'displayName')
        floor_id = get_attribute(xmlroot, 'floor')
        room_id = get_attribute(xmlroot, 'room')

        button_device = serialnumber + '/' + 'ch0000'
        if floor_id != '' and room_id != '' and self.use_room_names:
            button_name = button_basename + ' (' + roomnames[floor_id][room_id] + ')'
        else:
            button_name = button_basename

        channels = xmlroot.find('channels')
        if channels is not None:
            for channel in channels.findall('channel'):
                target_temperature = get_output_datapoint(channel, 'odp0006')
                current_temperature = get_output_datapoint(channel, 'odp0010')
                state = get_output_datapoint(channel, 'odp0008')
                eco_mode = get_output_datapoint(channel, 'odp0009')

        self.thermostat_devices[button_device] = FahThermostat(self, button_device, button_name,
                                                               temperature=current_temperature,
                                                               target=target_temperature,
                                                               state=state,
                                                               eco_mode=eco_mode)
        LOG.info('thermostat %s %s ', button_device, button_name)

    async def find_devices(self, use_room_names):
        """ Find the devices in the system, this is a big XML file   """
        self.use_room_names = use_room_names

        my_iq = await self.send_rpc_iq('RemoteInterface.getAll', 'de', 4, 0, 0)

        my_iq.enable('rpc_query')

        if my_iq['rpc_query']['method_response']['fault'] is not None:
            fault = my_iq['rpc_query']['method_response']['fault']
            LOG.info(fault['string'])
        else:
            args = xml2py(my_iq['rpc_query']['method_response']['params'])

            # deviceID
            #     'B002', // Schaltaktor 4-fach, 16A, REG
            #	  '100E', // Sensor/ Schaltaktor 2/1-fach
            #	  'B008', // Sensor/ Schaltaktor 8/8fach, REG
            #     '100C', // Sensor/schakelaktor 1/1-voudig
            #     'FFE7', // Sensor/schakelaktor 2/2-voudig
            #
            #     '10C4'  // Hue Aktor (Plug Switch)
            #
            #     '101C', // Dimmaktor 4-fach
            #     '1019', // Sensor/Dimmaktor 2/1-Fach          
            #	  '1021', // Dimmaktor 4-fach v2
            #     '1017'  // Sensor/dimaktor 1/1-voudig
            #     '10C0'  // Hue Aktor (LED Strip)
            #
            #     'B001', // Jalousieaktor 4-fach, REG
            #     '1013'  // Sensor/ Jalousieaktor 1/1-fach
            #     '1015'  // Sensor/ Jalousieaktor 2/1-fach

            self.found_devices = True

            root = ET.fromstring(args[0])

            # make a list of the rooms
            roomnames = get_room_names(root)

            # Now look for the devices
            device = root.find('devices')

            for neighbor in device.findall('device'):
                serialnumber = neighbor.get('serialNumber')
                device_id = neighbor.get('deviceId')

                # Switch actuators
                if (device_id == 'B002' or device_id == '100E' or device_id == 'B008' or
                        device_id == '900C' or device_id == '9010' or device_id == '4000' or
                        device_id == '10C4' or device_id == '100C' or device_id == '1010'):
                    self.add_light_device(neighbor, serialnumber, roomnames)

                # Dimming actuators
                # Hue Aktor (LED Strip), Sensor/dimaktor 1/1-voudig
                if (device_id == '101C' or device_id == '1021' or
                        device_id == '1014' or device_id == '901c' or
                        device_id == '9017' or device_id == '9019' or
                        device_id == '10C0' or device_id == '1017' or
                        device_id == '1019'):
                    self.add_dimmer_device(neighbor, serialnumber, roomnames)

                # Scene or Timer
                if device_id == '4800' or device_id == '4A00' or device_id == '4803' or \
                   device_id == '4A01' or device_id == '4804' or device_id == '4000' or \
                   device_id == '4802' or device_id == '4A00': 
                    self.add_scene(neighbor, serialnumber, roomnames)

                # blind/cover device
                if device_id == 'B001' or device_id == '1013' or device_id == '1015' or \
                        device_id == '9013' or device_id == '9015':
                    self.add_cover_device(neighbor, serialnumber, roomnames)

                # Sensor units 1/2 way
                if device_id == '1002' or device_id == '1000' or device_id == '100C' or \
                    device_id == '1019' or device_id == '1017' :
                    self.add_sensor_unit(neighbor, serialnumber, roomnames, device_id)

                # binary sensor
                if device_id == 'B005' or device_id == 'B006' or device_id == 'B007':
                    self.add_binary_sensor(neighbor, serialnumber, roomnames)

                # movement detector
                if device_id == '100A' or device_id == '9008' or device_id == '900A' or \
                   device_id == '1008':
                    self.add_movement_detector(neighbor, serialnumber, roomnames)

                # thermostat
                if device_id == '1004' or device_id == '9004':
                    self.add_thermostat(neighbor, serialnumber, roomnames)


class FreeAtHomeSysApp(object):
    """"  This class connects to the Busch Jeager Free @ Home sysapp
          parameters in configuration.yaml
          host       - Ip adress of the sysapp device
          username
          password
          use_room_names - Show room names with the devices
    """

    def __init__(self, host, port, user, password):
        """ x   """
        self._host = host
        self._port = port
        self._user = user
        self._jid = None
        self._password = password
        self.xmpp = None
        self._use_room_names = False

    @property
    def use_room_names(self):
        """ getter use_room_names   """
        return self._use_room_names

    @use_room_names.setter
    def use_room_names(self, value):
        """ setter user_room_names   """
        self._use_room_names = value

    def connect(self):
        """ connect to the Free@Home sysap   """
        settings = SettingsFah(self._host)
        self._jid = settings.get_jid(self._user)

        iterations = None
        salt = None

        LOG.info('Connect Free@Home  %s ', self._jid)

        if self._jid is not None:
            fahversion = settings.get_flag('version')

            if version.parse(fahversion) >= version.parse("2.3.0"):
                iterations, salt = settings.get_scram_settings(self._user, 'SCRAM-SHA-256')
            # create xmpp client
            self.xmpp = Client(self._jid, self._password, fahversion, iterations, salt)
            # connect
            self.xmpp.connect((self._host, self._port), False, False, False)

    async def wait_for_connection(self):
        """ Wait til connection is made, if failed at first attempt retry until success """
        if self.xmpp is not None:
            while self.xmpp.connect_ready() is False:
                LOG.info('waiting for connection')
                await asyncio.sleep(1)
            return self.xmpp.authenticated

    def get_devices(self, device_type):
        """ Get devices of a specific type from the sysap   """
        return self.xmpp.get_devices(device_type)

    async def find_devices(self):
        """ find all the devices on the sysap   """
        try:
            await self.xmpp.find_devices(self._use_room_names)
        except IqError as error:
            raise error
