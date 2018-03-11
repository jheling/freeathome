#!/usr/bin/python
# -*- coding: utf-8 -*-

import asyncio
import logging
import time
import slixmpp
from slixmpp import Message
from slixmpp.xmlstream import ElementBase, ET, JID, register_stanza_plugin
from slixmpp.plugins.xep_0009.binding import py2xml, xml2py, xml2fault, fault2xml
from slixmpp.plugins.xep_0009.stanza.RPC import RPCQuery, MethodCall, MethodResponse
from slixmpp.plugins.xep_0009 import stanza
from slixmpp.plugins.xep_0060.stanza.pubsub_event import Event, EventItems, EventItem
from slixmpp.exceptions import IqError, IqTimeout
from slixmpp import Iq
from slixmpp import future_wrapper
import urllib.request, json
import xml.etree.ElementTree as ET
import urllib.request, json

log = logging.getLogger(__name__)

class ItemUpdate(ElementBase):
    namespace = 'http://abb.com/protocol/update'
    name = 'update'
    plugin_attrib = name
    interfaces = set(('data'))

def data2py(update):
    namespace = 'http://abb.com/protocol/update'
    vals = []
    for data in update.xml.findall('{%s}data' % namespace):
        vals.append(data.text)
    return vals

class Client(slixmpp.ClientXMPP):    

    found_devices = False
    # All the devices and the types
    devices = {}    
    # The specific devices 
    light_devices = {}
    scene_devices = {}
    switch_devices = {}
    connect_finished = False
    
    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # register plugins
        self.register_plugin('xep_0030')  # RPC
        self.register_plugin('xep_0060') # PubSub
        
        register_stanza_plugin(Iq, RPCQuery)
        register_stanza_plugin(RPCQuery, MethodCall)
        register_stanza_plugin(RPCQuery, MethodResponse)

        register_stanza_plugin(Message, Event)
        register_stanza_plugin(Event, EventItems)
        register_stanza_plugin(EventItems, EventItem, iterable=True)
        register_stanza_plugin(EventItem, ItemUpdate)

        # handle session_start and message events
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("roster_update", self.roster_callback)
        self.add_event_handler("pubsub_publish", self.pub_sub_callback)
        
    def connect_ready(self):
        return self.connect_finished
      
    @asyncio.coroutine    
    def start(self, event):
        # The connect has succeeded
       
        log.info('send presence') 
        self.send_presence()

        self.send_presence_subscription(pto="mrha@busch-jaeger.de/rpc", pfrom=self.boundjid.full)

        self.send('<presence xmlns="jabber:client"><c xmlns="http://jabber.org/protocol/caps" ver="1.0" node="http://gonicus.de/caps"/></presence>') 
        
        log.info('get roster')
        self.get_roster()
    
    @asyncio.coroutine
    def turn_on(self, device):
        yield from self.set_datapoint(device,'idp0000', '1')
        self.light_devices[device]['state'] = True

        if self.light_devices[device]['light_type'] == 'dimmer':
            yield from self.set_datapoint(device,'idp0002', str(self.light_devices[device]['brightness']) )

    def set_brightness(self,device, brightness):
        if self.light_devices[device]['light_type'] == 'dimmer':
            self.light_devices[device]['brightness'] = brightness

    @asyncio.coroutine
    def turn_off(self, device):
        yield from self.set_datapoint(device ,'idp0000', '0')
        self.light_devices[device]['state'] = False
     
    @asyncio.coroutine
    def activate(self, device):
        yield from self.set_datapoint(device ,'odp0000', '1')
          
    @asyncio.coroutine
    def update(self, device):
        return

    def is_on(self, device):
        return self.light_devices[device]['state']

    @asyncio.coroutine
    def set_datapoint(self, device,datapoint,command):
        
        log.info("set_datapoint %s %s %s",device, datapoint, command)

        name = device + '/' + datapoint
        
        try:
            yield from self.send_rpc_iq('RemoteInterface.setDatapoint',name, command ,callback=self.rpc_callback)
        except IqError as e:
            raise e                    

    def get_devices(self, device_type, use_room_names):

        if device_type == 'light':
            return self.light_devices

        if device_type == 'scene':        
            return self.scene_devices

        if device_type == 'switch':
            return self.switch_devices           
        
    def send_rpc_iq(self,command,*argv,
                  timeout=None, callback=None,
                  timeout_callback=None):
        
        iq = self.make_iq_set()
        iq['to'] = 'mrha@busch-jaeger.de/rpc'
        iq['from'] = self.boundjid.full
        iq.enable('rpc_query')
        iq['rpc_query']['method_call']['method_name'] = command
        iq['rpc_query']['method_call']['params'] = py2xml(*argv)        

        return iq.send(timeout=timeout, callback=callback,timeout_callback=timeout_callback)
    
    def roster_callback(self, roster_iq):
        log.info("Roster callback ")
        self.connect_finished = True         
    
    
    def pub_sub_callback(self, msg):
         
        if msg['pubsub_event']['items']['item']['update']['data'] is not None:

          args = data2py(msg['pubsub_event']['items']['item']['update'])   
          
          # arg contains the devices that changed 
          root = ET.fromstring(args[0])
          
          device = root.find('devices')  
          for neighbor in device.findall('device'): 
              serialNumber = neighbor.get('serialNumber')

              channels = neighbor.find('channels')
              if channels is not None:
                  for channel in channels.findall('channel'):
                      channelId   = channel.get('i')

                      # get the inputs
                      inputs = channel.find('inputs')
                      idatapoint = inputs.find('dataPoint')
                      inputPoints = {}
                      if idatapoint is not None:
                          inputId = idatapoint.get('i')
                          inputValue = idatapoint.find('value').text
                          inputPoints[inputId] = inputValue

                      # get the outputs
                      outputs = channel.find('outputs')
                      odatapoint = outputs.find('dataPoint')
                      outputPoints = {}
                      if odatapoint is not None:
                          outputId = odatapoint.get('i')
                          outputValue = odatapoint.find('value').text
                          outputPoints[outputId] = outputValue

                      # Now change the status of the device
                      device_id = serialNumber + '/' + channelId
                                        
                      # if the device is a light                  
                      if device_id in self.light_devices:
                          if 'idp0000' in inputPoints:
                              if inputPoints['idp0000'] == '1':
                                  state = True
                              else:
                                  state = False
        
                              self.light_devices[device_id]['state'] = state

                              log.info("device %s (%s) is %s", self.light_devices[device_id]['name'],  device_id, state)
                              
                          if 'odp0001' in outputPoints:
                              self.light_devices[device_id]['brightness'] =  outputPoints['odp0001']
                              log.info("device %s (%s) brightness %s", self.light_devices[device_id]['name'],  device_id, self.light_devices[device_id]['brightness'])
                         
    def rpc_callback(self, iq):
        iq.enable('rpc_query')
        
        if iq['rpc_query']['method_response']['fault'] is not None:
            fault = iq['rpc_query']['method_response']['fault']
            log.info(fault['string'])
        else:        
            result = xml2py(iq['rpc_query']['method_response']['params'])
            log.info('method response: %s',result[0])  
    
    def setlight_callback(self, iq):
        log.info("setlight callback ")

    def add_light_info(self, name = None, state = False, floor = None, room = None, light_type = 'normal', brightness = None):
        light_info = {}
        light_info['name'] = name        
        light_info['state'] = state
        light_info['floor'] = floor
        light_info['room'] = room
        light_info['light_type'] = light_type
        light_info['brightness'] = brightness
        return light_info
        
    def add_scene_info(self, name = None, floor = None, room = None):
        scene_info = {}
        scene_info['name'] = name        
        scene_info['floor'] = floor
        scene_info['room'] = room        
        return scene_info
        
    @asyncio.coroutine
    def find_devices(self, use_room_names):    
        
        iq = yield from self.send_rpc_iq('RemoteInterface.getAll','de',4,0,0)

        iq.enable('rpc_query')
        
        if iq['rpc_query']['method_response']['fault'] is not None:
            fault = iq['rpc_query']['method_response']['fault']
            log.info(fault['string'])
        else:        
            args = xml2py(iq['rpc_query']['method_response']['params'])

            """
              deviceID
                 'B002', // Schaltaktor 4-fach, 16A, REG
		         '100E', // Sensor/ Schaltaktor 2/1-fach
		         'B008', // Sensor/ Schaltaktor 8/8fach, REG
                 '10C4' // Hue Aktor (Plug Switch)

                 '101C', // Dimmaktor 4-fach
		         '1021', // Dimmaktor 4-fach v2
                 '10C0' // Hue Aktor (LED Strip)

                 'B001', // Jalousieaktor 4-fach, REG
                 '1013' // Sensor/ Jalousieaktor 1/1-fach

            """

            self.found_devices = True   

            root = ET.fromstring(args[0])

            strings = root.find('strings')

            # Store all the names
            names = {}            
            for string in strings.findall('string'):
                stringNameId = string.get('nameId')
                stringValue  = string.text
                names[stringNameId] = stringValue
                
            # make a list of the rooms
            floorplan = root.find('floorplan') 
            floornames = {}
            roomnames  = {} 
            
            for floor in floorplan.findall('floor'):
                FloorName = floor.get('name')
                FloorUid  = floor.get('uid') 
                floornames[FloorUid] = FloorName
                log.info(' floor %s', FloorName) 
            
                roomnames[FloorUid] = {}     
                # Now the rooms of this floor
                for room in floor.findall('room'):
                    RoomName = room.get('name')
                    RoomUid  = room.get('uid') 
                    roomnames[FloorUid][RoomUid] = RoomName

            # Now look for the devices        
            device = root.find('devices')

            for neighbor in device.findall('device'):                
                serialNumber = neighbor.get('serialNumber')
                nameId       = names[neighbor.get('nameId')].title()
                deviceId     = neighbor.get('deviceId')

                # Schaltaktor 4-fach, 16A, REG
                if deviceId == 'B002' or deviceId == '100E' or deviceId == 'B008' or deviceId == '10C4':  
                    # Now the channels of a device
                    channels = neighbor.find('channels')         

                    if channels is not None:
                        for channel in channels.findall('channel'):
                            channelName = names[channel.get('nameId')].title()
                            channelId   = channel.get('i')
                        
                            light_name = ''
                            floorId    = ''
                            roomId     = ''
                            for attributes in channel.findall('attribute'):
                                attributeName  = attributes.get('name')
                                attributeValue = attributes.text

                                if attributeName == 'displayName': 
                                    light_name = attributeValue
                                if attributeName == 'floor':
                                    floorId = attributeValue
                                if attributeName == 'room':
                                    roomId = attributeValue

                            inputs = channel.find('inputs')    
                            for datapoints in inputs.findall('dataPoint'):
                                datapointId = datapoints.get('i')
                                datapointValue = datapoints.find('value').text
                                if datapointId == 'idp0000':
                                    if datapointValue == '1':
                                       light_state = True
                                    else:
                                       light_state = False
                                                             
                            single_light = serialNumber + '/' + channelId 
                            if light_name == '':
                                light_name = single_light
                            if floorId != '' and roomId != '' and use_room_names == True:
                                light_name = light_name + ' (' + roomnames[floorId][roomId] + ')'
                                                                                  
                                self.light_devices[single_light] = self.add_light_info(name = light_name, state = light_state , floor = floornames[floorId], room = roomnames[floorId][roomId])
                            else:
                                self.light_devices[single_light] = self.add_light_info(name = light_name, state = light_state , floor = '', room = '')                            

                            self.devices[single_light] = 'light'   
                            log.info( 'light  %s %s is %s',single_light ,light_name, light_state )

                # Dimmaktor 4-fach and Dimmaktor 4-fach v2 
                if deviceId == '101C' or  deviceId == '1021' or deviceId == '10C0':
                    # Now the channels of a device
                    channels = neighbor.find('channels')         

                    if channels is not None:
                        for channel in channels.findall('channel'):
                            channelName = names[channel.get('nameId')].title()
                            channelId   = channel.get('i')
                                                    
                            light_name = ''
                            floorId    = ''
                            roomId     = ''
                            brightness = None
                            for attributes in channel.findall('attribute'):
                                attributeName  = attributes.get('name')
                                attributeValue = attributes.text

                                if attributeName == 'displayName': 
                                    light_name = attributeValue
                                if attributeName == 'floor':
                                    floorId = attributeValue
                                if attributeName == 'room':
                                    roomId = attributeValue

                            inputs = channel.find('inputs')    
                            for datapoints in inputs.findall('dataPoint'):
                                datapointId = datapoints.get('i')
                                datapointValue = datapoints.find('value').text
                                if datapointId == 'idp0000':
                                    if datapointValue == '1':
                                       light_state = True
                                    else:
                                       light_state = False

                            outputs = channel.find('outputs')    
                            for datapoints in inputs.findall('dataPoint'):
                                datapointId = datapoints.get('i')
                                datapointValue = datapoints.find('value').text
                                if datapointId == 'odp0001':
                                    brightness = datapointValue
                                
                            single_light = serialNumber + '/' + channelId 
                            if light_name == '':
                                light_name = single_light
                            if floorId != '' and roomId != '' and use_room_names == True:
                                light_name = light_name + ' (' + roomnames[floorId][roomId] + ')'                                                                                    
                                self.light_devices[single_light] = self.add_light_info(name = light_name, state = light_state , floor = floornames[floorId], room = roomnames[floorId][roomId], light_type = 'dimmer', brightness = brightness)
                            else:
                                self.light_devices[single_light] = self.add_light_info(name = light_name, state = light_state , floor = '', room = '', light_type = 'dimmer', brightness = brightness)
                                        
                            self.devices[single_light] = 'light'                                        
                            log.info( 'dimmer %s %s is %s',single_light ,light_name, light_state )
 
                # Scene or Timer  
                if deviceId == '4800' or deviceId == '4A00':
                    channels = neighbor.find('channels')           

                    if channels is not None:
                        for channel in channels.findall('channel'):
                            channelName = names[channel.get('nameId')].title()
                            channelId   = channel.get('i')
                        
                            scene_name = ''
                            floorId    = ''
                            roomId     = ''
                            for attributes in channel.findall('attribute'):
                                attributeName  = attributes.get('name')
                                attributeValue = attributes.text            
                
                                if attributeName == 'displayName': 
                                    scene_name = attributeValue
                                if attributeName == 'floor':
                                    floorId = attributeValue
                                if attributeName == 'room':                            
                                    roomId = attributeValue

                            scene = serialNumber + '/' + channelId
                            if scene_name == '':
                                scene_name = scene

                            if floorId != '' and roomId != '' and use_room_names == True:
                                scene_name = scene_name + ' (' + roomnames[floorId][roomId] + ')'                                                                                    
                                self.scene_devices[scene] = self.add_scene_info(name = scene_name, floor = floornames[floorId], room = roomnames[floorId][roomId])
                            else:
                                self.scene_devices[scene] = self.add_scene_info(name = scene_name, floor = '', room = '') 

                            self.devices[scene] = 'scene'   
                            log.info( 'scene  %s %s',scene ,scene_name )    
                # switch device
            
             
            # Store the devices in a dictionary    

class freeathomesysapp(object):
    """"  This class connects to the Busch Jeager Free @ Home sysapp
          parameters in configuration.yaml
          host       - Ip adress of the sysapp device
          username
          password           
          use_room_names - Show room names with the devices
    """ 

    def __init__(self, host,port,user,password, use_room_names ):
        self._host = host
        self._port = port
        self._user = user
        self._jid  = None
        self._password = password        
        self.xmpp = None 
        self._use_room_names = use_room_names

    def get_jid(self):
        http = 'http://' + self._host + '/settings.json'    
        with urllib.request.urlopen(http) as url:
            data = json.loads(url.read().decode())    

            usernames = data['users']
            for key in usernames:        
                if key['name'] == self._user:
                    self._jid = key['jid']
                        
    def connect(self):
        self.get_jid() 
        
        log.info('Connect Free@Home  %s ', self._jid)        
        
        if self._jid is not None:
          # create xmpp client
          self.xmpp = Client(self._jid, self._password)
          # connect
          self.xmpp.connect((self._host, self._port))          

    @asyncio.coroutine
    def wait_for_connection(self):
        while self.xmpp.connect_ready() == False:
            log.info('wait for connection')   
            yield from asyncio.sleep(0.5)
          
    @asyncio.coroutine
    def turn_on(self, device): 
        yield from self.xmpp.turn_on(device)

    def set_brightness(self, device, brightness): 
        self.xmpp.set_brightness(device, brightness)

    def get_brightness(self, device): 
        return int(self.xmpp.devices[device]['brightness'])

    @asyncio.coroutine
    def turn_off(self, device):
        yield from self.xmpp.turn_off(device) 
     
    @asyncio.coroutine
    def activate(self, device):
        yield from self.xmpp.activate(device) 
        
    @asyncio.coroutine
    def update(self, device):
        yield from self.xmpp.update(device)
        return
     
    def is_on(self, device):
        return self.xmpp.is_on(device)

    def get_devices(self,device_type):                 
        return self.xmpp.get_devices(device_type, self._use_room_names)

    @asyncio.coroutine
    def find_devices(self):        
        try: 
            yield from self.xmpp.find_devices(self._use_room_names)
        except IqError as e:
            raise e        
