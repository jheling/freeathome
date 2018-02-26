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

    state = False
    devices = {}

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
        self.add_event_handler("roster_update_complete", self.roster_callback)
        self.add_event_handler("pubsub_publish", self.pub_sub_callback)
        
    @asyncio.coroutine    
    def start(self, event):
        
        self.send_presence()

        self.send_presence_subscription(pto="mrha@busch-jaeger.de/rpc", pfrom=self.boundjid.full)

        self.send('<presence xmlns="jabber:client"><c xmlns="http://jabber.org/protocol/caps" ver="1.0" node="http://gonicus.de/caps"/></presence>') 
        
        self.get_roster()
    
    @asyncio.coroutine
    def turn_on(self, device):
        yield from self.set_light(device + '/idp0000', 'on')
        self.devices[device]['state'] = True

    @asyncio.coroutine
    def turn_off(self, device):
        yield from self.set_light(device  + '/idp0000', 'off')
        self.devices[device]['state'] = False
     
    @asyncio.coroutine
    def update(self, device):
        return

    def is_on(self, device):
        return self.devices[device]['state']

    @asyncio.coroutine
    def set_light(self, device,command):
        
        log.info("set_light %s %s ",device, command)

        if command  == 'on':
            ivalue = '1'      
        else:
            ivalue = '0'
        try:
            yield from self.send_rpc_iq('RemoteInterface.setDatapoint',device,ivalue ,callback=self.rpc_callback)
        except IqError as e:
            raise e
        else:
            log.info('after send_rpc_iq: %s', ivalue)            

    @asyncio.coroutine 
    def get_devices(self, use_room_names):

        try: 
            yield from self.find_devices(use_room_names)
        except IqError as e:
            raise e
        else:
          return self.devices

    def send_rpc_iq(self,command,*argv,
                  timeout=None, callback=None,
                  timeout_callback=None):
        log.setLevel(10)         
 
        log.info("send_rpc_iq %s", command)        
 
        iq = self.make_iq_set()
        iq['to'] = 'mrha@busch-jaeger.de/rpc'
        iq['from'] = self.boundjid.full
        iq.enable('rpc_query')
        iq['rpc_query']['method_call']['method_name'] = command
        iq['rpc_query']['method_call']['params'] = py2xml(*argv)        

        return iq.send(timeout=timeout, callback=callback,timeout_callback=timeout_callback)
    
    def roster_callback(self, roster_iq):
        log.debug("Roster callback ")
                
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
                      if odatapoint is not None:
                          outputId = odatapoint.get('i')
                          outputValue = odatapoint.find('value').text  

                      # Now change the status of the device
                      single_light = serialNumber + '/' + channelId
                      if single_light in self.devices and 'idp0000' in inputPoints:
                          if inputPoints['idp0000'] == '1':
                              state = True
                          else:
                              state = False
    
                          self.devices[single_light]['state'] = state                              
                         
    def rpc_callback(self, iq):
        log.info("rpc callback") 
    
    def setlight_callback(self, iq):
        log.info("setlight callback ")

    def add_light_info(self, name = None, state = False, floor = None, room = None):
        light_info = {}
        light_info['name'] = name        
        light_info['state'] = state
        light_info['floor'] = floor
        light_info['room'] = room
        return light_info
        
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

            log.info(len(args))   

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
                            roomId       = ''
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
                                                                                  
                                self.devices[single_light] = self.add_light_info(name = light_name, state = light_state , floor = floornames[floorId], room = roomnames[floorId][roomId])
                            else:
                                self.devices[single_light] = self.add_light_info(name = light_name, state = light_state , floor = '', room = '')                            

                            log.info( 'light %s %s',single_light ,light_name )

                # Dimmaktor 4-fach and Dimmaktor 4-fach v2 
                if deviceId == '101C' or  deviceId == '1021' or deviceId == '10C0':
                    # Now the channels of a device
                    channels = neighbor.find('channels')         

                    if channels is not None:
                        for channel in channels.findall('channel'):
                            channelName = names[channel.get('nameId')].title()
                            channelId   = channel.get('i')
                            log.info("    %s %s",channelId, channelName)
                        
                            for attributes in channel.findall('attribute'):
                                attributeName  = attributes.get('name')
                                attributeValue = attributes.text
                                log.info("      %s %s",attributeName, attributeValue)

                            light_name = ''
                            floorId      = ''
                            roomId       = ''
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
                                self.devices[single_light] = self.add_light_info(name = light_name, state = light_state , floor = floornames[floorId], room = roomnames[floorId][roomId])
                            else:
                                self.devices[single_light] = self.add_light_info(name = light_name, state = light_state , floor = '', room = '')
                                           
                            log.info( ' dimmer light %s %s',single_light ,light_name )
            
            # Store the devices in a dictionary    

class freeathomesysapp(object):
    """"  This class connects to the Busch Jeager Free @ Home sysapp
          parameters in configuration.yaml
          host       - Ip adress of the sysapp device
          username
          password           
    
    """ 

    def __init__(self, host,port,user,password, use_room_names ):
        self._host = host
        self._port = port
        self._user = user
        self._jid  = None
        self._password = password        
        self.xmpp = None 
        self.devices = None
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
    def turn_on(self, device): 
        yield from self.xmpp.turn_on(device)

    @asyncio.coroutine
    def turn_off(self, device):
        yield from self.xmpp.turn_off(device) 
     
    @asyncio.coroutine
    def update(self, device):
        yield from self.xmpp.update(device)
        return
     
    def is_on(self, device):
        return self.xmpp.is_on(device)

    @asyncio.coroutine
    def get_devices(self):
        devices = yield from self.xmpp.get_devices(self._use_room_names)
        return devices  

