#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Dann Martens
    This file is part of SleekXMPP.
    See the file LICENSE for copying permission.
"""
from slixmpp.plugins.xep_0009.binding import py2xml, xml2py, xml2fault, fault2xml
import logging
import slixmpp
from slixmpp import asyncio
from slixmpp import Message
from slixmpp.plugins.xep_0009 import stanza
from slixmpp.exceptions import IqError, IqTimeout
from slixmpp.plugins.xep_0009.stanza.RPC import RPCQuery, MethodCall, MethodResponse
from slixmpp.plugins.xep_0060.stanza.pubsub_event import Event, EventItems, EventItem
import xml.etree.ElementTree as ET
from slixmpp import Iq
from slixmpp import future_wrapper
from slixmpp.xmlstream import XMLStream

import time
import urllib.request, json
from slixmpp import Iq
from slixmpp.xmlstream import ElementBase, ET, JID, register_stanza_plugin

log = logging.getLogger(__name__)

class ItemUpdate(ElementBase):
    namespace = 'http://abb.com/protocol/update'
    name = 'update'
    plugin_attrib = name
    interfaces = set(('data'))

def get_jid( host, name):
    data = None
    jid  = None
    http = 'http://' + host + '/settings.json'
    try:
        with urllib.request.urlopen(http) as url:
            data = json.loads(url.read().decode())    

    except EnvironmentError: # parent of IOError, OSError *and* WindowsError where available
      print ('server not found')                

    if data is not None:
        usernames = data['users']
        for key in usernames:        
            if key['name'] == name:
               jid = key['jid']

        if jid is None:
            print('user not found')
        else:
            return jid

def data2py(update):
    namespace = 'http://abb.com/protocol/update'
    vals = []
    for data in update.xml.findall('{%s}data' % namespace):
        vals.append(data.text)
    return vals

class Client(slixmpp.ClientXMPP):
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
        self.add_event_handler("message", self.message)
        self.add_event_handler("roster_update_complete", self.roster_callback) 
        self.add_event_handler("pubsub_publish", self.pub_sub_callback)
         
    @asyncio.coroutine    
    def start(self, event):

        log.debug("begin session start")
        
        yield from self.presence_and_roster()             

        yield from self.rpc()  

        # Opbouwen van de parameters
        log.debug("Test start ")

    @asyncio.coroutine        
    def presence_and_roster(self):

        log.debug("begin p en r")
        
        self.send_presence()
        #self.get_roster() 

        self.send_presence_subscription(pto="mrha@busch-jaeger.de/rpc", pfrom=self.boundjid.full)

        self.send('<presence xmlns="jabber:client"><c xmlns="http://jabber.org/protocol/caps" ver="1.0" node="http://gonicus.de/caps"/></presence>') 
        
        try: 
            yield from self.get_roster()
        except IqError as e:
            raise e
        
        log.debug("eind p en r")

    def send_rpc_iq(self, timeout=None, callback=None,
                  timeout_callback=None):
        
        iq = self.make_iq_set()
        iq['to'] = 'mrha@busch-jaEger.de/rpc'
        iq['from'] = self.boundjid.full
        iq.enable('rpc_query')
        iq['rpc_query']['method_call']['method_name'] = 'RemoteInterface.getAll'
        iq['rpc_query']['method_call']['params'] = py2xml('de',4,0,0)        

        return iq.send(timeout=timeout, callback=callback,timeout_callback=timeout_callback)

    def rpc(self):

        log.debug("rpc")
        
        try:
            yield from self.send_rpc_iq(callback=self.rpc_callback)
        except IqError as e:
            raise e        
        
    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            msg.reply("You sent: %s" % msg['body']).send()

    def pub_sub_callback(self, msg):
         
        if msg['pubsub_event']['items']['item']['update']['data'] is not None:             

          args = data2py(msg['pubsub_event']['items']['item']['update'])   

          if args: 
            log.info('type %s list: %s',type(args),args)
          
            # arg contains the devices that changed 
            root = ET.fromstring(args[0])
          
    def roster_callback(self, roster_iq):
        log.debug("Rpc jhe ")
        # self.send_rpc_iq()

        try:
            rtt = yield from self.rpc()
            logging.info("Success! RTT: %s", rtt)
        except IqError as e:
            logging.info("Error rpd : %s",
                    e.iq['error']['condition'])
        except IqTimeout:
            logging.info("No response")
        #finally:
        #    self.disconnect()

    def rpc_callback(self, iq):    
        log.info("Rpc callback jhe ")
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
            # Nu een iteratie over de devices
            root = ET.fromstring(args[0])

            filename = 'mastermessage.xml'
            with open(filename,'w', encoding="utf-8") as file_object:
              file_object.write(args[0])

            for child in root:
                log.info(child.tag)

            strings = root.find('strings')

            # Zet de strings in een dictionary
            names = {}
            
            for string in strings.findall('string'):
                stringNameId = string.get('nameId')
                stringValue  = string.text
                names[stringNameId] = stringValue
                
            #log.info("%s", names)

            device = root.find('devices')

            for neighbor in device.findall('device'):                
                serialNumber = neighbor.get('serialNumber')
                nameId       = names[neighbor.get('nameId')].title()
                deviceId     = neighbor.get('deviceId')
                log.info("  %s %s %s %s",serialNumber,neighbor.get('nameId'),nameId,deviceId)

                # Schaltaktor 4-fach, 16A, REG
                if deviceId == 'B002':  
                    # Nu de channnels binnen een device
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

                            inputs = channel.find('inputs')    
                            for datapoints in inputs.findall('dataPoint'):
                                datapointId = datapoints.get('i')
                                datapointValue = datapoints.find('value').text
                                if datapointId == 'idp0000':
                                    if datapointValue == '1':
                                       light_state = True
                                    else:
                                       light_state = False   

                                log.info("        %s %s %s",datapointId, datapointValue, light_state) 
                                    
                # Dimmaktor 4-fach and Dimmaktor 4-fach v2 
                if deviceId == '101C' or  deviceId == '1021':
                    # Nu de channnels binnen een device
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

                            inputs = channel.find('inputs')    
                            for datapoints in inputs.findall('dataPoint'):
                                datapointId = datapoints.get('i')
                                datapointValue = datapoints.find('value').text
                                if datapointId == 'idp0000':
                                    if datapointValue == '1':
                                       light_state = True
                                    else:
                                       light_state = False   

                                log.info("        %s %s %s",datapointId, datapointValue, light_state) 


                # switch
                if deviceId == '1002' or deviceId == '1000' or deviceId == '100A':
                    # Nu de channnels binnen een device
                    channels = neighbor.find('channels')                     
                    
        #mes = self.get_params 
        
        # log.info(mes)
        #self.disconnect()    
             
def main():
    # set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')

    ipadress = 'xx.xx.xx.xx' 
    username = '' # exact username, case sensitive
    password = ''
    jid = get_jid(ipadress, username) 

    # create xmpp client
    xmpp = Client(jid, password)
    # connect
    xmpp.connect((ipadress, 5222))

    #log.info(' %s %s', type(result), result )
    
    xmpp.process(forever=True)    

if __name__ == '__main__':
    main()
