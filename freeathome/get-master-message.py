#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Dann Martens
    This file is part of SleekXMPP.
    See the file LICENSE for copying permission.
"""
import logging
import slixmpp
import sys
import zlib
# import fah
# from slixmpp import asyncio
from slixmpp import Message
from slixmpp.exceptions import IqError
# , IqTimeout
from slixmpp.plugins.xep_0009.stanza.RPC import RPCQuery, MethodCall, MethodResponse
from slixmpp.plugins.xep_0009.binding import py2xml, xml2py
from slixmpp.plugins.xep_0060.stanza.pubsub_event import Event, EventItems, EventItem
from slixmpp.xmlstream import ElementBase, ET, register_stanza_plugin
 # JID,
from slixmpp import Iq
from packaging import version

from fah.messagereader import MessageReader
from fah.saslhandler import SaslHandler
from fah.settings import SettingsFah

log = logging.getLogger(__name__)


class ItemUpdate(ElementBase):
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


class Client(slixmpp.ClientXMPP):
    def __init__(self, jid, password, fahversion, iterations=None, salt=None):
        slixmpp.ClientXMPP.__init__(self, jid, password, sasl_mech='SCRAM-SHA-1')

        self.fahversion = fahversion     
        self.x_jid = jid

        log.info(' version: %s', self.fahversion)
        
        if version.parse(self.fahversion) >= version.parse("2.3.0"):
            self.saslhandler = SaslHandler(self, jid, password, iterations, salt)
                       
        # register plugins
        self.register_plugin('xep_0030')  # RPC
        self.register_plugin('xep_0060')  # PubSub
        # self.register_plugin('xep_0199', {'keepalive': True, 'interval': 10})
        
        register_stanza_plugin(Iq, RPCQuery)
        register_stanza_plugin(RPCQuery, MethodCall)
        register_stanza_plugin(RPCQuery, MethodResponse)

        register_stanza_plugin(Message, Event)
        register_stanza_plugin(Event, EventItems)
        register_stanza_plugin(EventItems, EventItem, iterable=True)
        register_stanza_plugin(EventItem, ItemUpdate)
        register_stanza_plugin(EventItem, ItemUpdateEncrypted)

        # handle session_start and message events
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("pubsub_publish", self.pub_sub_callback)

    async def start(self, event):
        log.debug("begin session start")

        if version.parse(self.fahversion) >= version.parse("2.3.0"):
            await self.saslhandler.initiate_key_exchange()  

        await self.presence_and_roster()

        await self.rpc()
     
    async def presence_and_roster(self):
        log.info("start presence and roster")
        
        self.send_presence()

        self.send_presence_subscription(pto="mrha@busch-jaeger.de/rpc", pfrom=self.boundjid.full)

        self.send('<presence xmlns="jabber:client"><c xmlns="http://jabber.org/protocol/caps" ver="1.1" node="http://gonicus.de/caps"/></presence>') 

        log.info("end presence and roster")
        
    def send_rpc_iq(self, timeout=None, callback=None, timeout_callback=None):
        iq = self.make_iq_set()
        iq['to'] = 'mrha@busch-jaeger.de/rpc'
        iq['from'] = self.boundjid.full
        iq.enable('rpc_query')
        iq['rpc_query']['method_call']['method_name'] = 'RemoteInterface.getAll'
        iq['rpc_query']['method_call']['params'] = py2xml('de', 4, 0, 0)

        return iq.send(timeout=timeout, callback=callback, timeout_callback=timeout_callback)

    async def rpc(self):
        log.debug("rpc")
        
        try:
            await self.send_rpc_iq(callback=self.rpc_callback)
        except IqError as e:
            raise e

    def message(self, msg):
        log.info('message received')
        # log.info(msg)

        if msg['type'] in ('chat', 'normal', 'headline'):
            msg.reply("You sent: %s" % msg['body']).send()

    def pub_sub_callback(self, msg):
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
                        print(e)
                    except:
                        print('error zlib.decompress ',  sys.exc_info()[0])
                    else:
                        if len(unzipped) != length:
                            log.info("Unexpected uncompressed data length, have=" + str(len(unzipped)) + ", expected=" + str(length))
                        mes = unzipped.decode('utf-8')
                        print(mes)
        else:                 
            if msg['pubsub_event']['items']['item']['update']['data'] is not None:
                args = data2py(msg['pubsub_event']['items']['item']['update'])   

                if args: 
                    log.info('type %s list: %s', type(args), args)
              
                    # arg contains the devices that changed
                    root = ET.fromstring(args[0])
    '''
    def roster_callback(self, roster_iq):
        log.debug("Rpc jhe ")
        # self.send_rpc_iq()
        
        try:
            rtt = await self.rpc()
            logging.info("Success! RTT: %s", rtt)
        except IqError as e:
            logging.info("Error rpd : %s",
                    e.iq['error']['condition'])
        except IqTimeout:
            logging.info("No response")
            
        #finally:
        #    self.disconnect()
    '''

    def rpc_callback(self, iq):    
        log.info("Rpc callback jhe ")
        iq.enable('rpc_query')
          
        if iq['rpc_query']['method_response']['fault'] is not None:
            fault = iq['rpc_query']['method_response']['fault']
            log.info(fault['string'])
        else:
            if iq['rpc_query']['method_response']['params'] is not None:
            
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
                with open(filename, 'w', encoding="utf-8") as file_object:
                    file_object.write(args[0])

                for child in root:
                    log.info(child.tag)

                strings = root.find('strings')

                # Zet de strings in een dictionary
                names = {}
                
                for string in strings.findall('string'):
                    stringNameId = string.get('nameId')
                    stringValue = string.text
                    names[stringNameId] = stringValue

                # log.info("%s", names)

                device = root.find('devices')

                for neighbor in device.findall('device'):                
                    serialNumber = neighbor.get('serialNumber')
                    nameId = names[neighbor.get('nameId')].title()
                    deviceId = neighbor.get('deviceId')
                    log.info("  %s %s %s %s", serialNumber, neighbor.get('nameId'), nameId, deviceId)

                    # Schaltaktor 4-fach, 16A, REG
                    if deviceId == 'B002':  
                        # Nu de channnels binnen een device
                        channels = neighbor.find('channels')         

                        if channels is not None:
                            for channel in channels.findall('channel'):
                                channelName = names[channel.get('nameId')].title()
                                channelId = channel.get('i')
                                log.info("    %s %s", channelId, channelName)
                            
                                for attributes in channel.findall('attribute'):
                                    attributeName = attributes.get('name')
                                    attributeValue = attributes.text
                                    log.info("      %s %s", attributeName, attributeValue)

                                inputs = channel.find('inputs')    
                                for datapoints in inputs.findall('dataPoint'):
                                    light_state = False
                                    datapointId = datapoints.get('i')
                                    datapointValue = datapoints.find('value').text
                                    if datapointId == 'idp0000':
                                        if datapointValue == '1':
                                            light_state = True

                                    log.info("        %s %s %s", datapointId, datapointValue, light_state)
                                        
                    # Dimmaktor 4-fach and Dimmaktor 4-fach v2 
                    if deviceId == '101C' or deviceId == '1021':
                        # The channels within a device
                        channels = neighbor.find('channels')         

                        if channels is not None:
                            for channel in channels.findall('channel'):
                                channelName = names[channel.get('nameId')].title()
                                channelId = channel.get('i')
                                log.info("    %s %s", channelId, channelName)

                                for attributes in channel.findall('attribute'):
                                    attributeName = attributes.get('name')
                                    attributeValue = attributes.text
                                    log.info("      %s %s", attributeName, attributeValue)

                                inputs = channel.find('inputs')    
                                for datapoints in inputs.findall('dataPoint'):
                                    light_state = False
                                    datapointId = datapoints.get('i')
                                    datapointValue = datapoints.find('value').text
                                    if datapointId == 'idp0000':
                                        if datapointValue == '1':
                                            light_state = True

                                    log.info("        %s %s %s", datapointId, datapointValue, light_state)

                    # switch
                    if deviceId == '1002' or deviceId == '1000' or deviceId == '100A':
                        # Now the channels within a device
                        channels = neighbor.find('channels')                     
                
        # mes = self.get_params
        
        # log.info(mes)
        # self.disconnect()


def main():
    # set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')

    ipaddress = 'xx.xx.xx.xx'
    username = ''  # exact username, case sensitive
    password = ''
    iterations = None
    salt = None

    settings = SettingsFah(ipaddress)
    jid = settings.get_jid(username) 
    fahversion = settings.get_flag('version')

    if version.parse(fahversion) >= version.parse("2.3.0"):
        iterations, salt = settings.get_scram_settings(username, 'SCRAM-SHA-256')
        
    log.info(' %s %s %s', fahversion, iterations, salt)

    # create xmpp client
    xmpp = Client(jid, password, fahversion, iterations, salt)
    # connect
    xmpp.end_session_on_disconnect = False
    xmpp.connect((ipaddress, 5222), force_starttls=False)
    
    xmpp.process(forever=True)    


if __name__ == '__main__':
    main()
