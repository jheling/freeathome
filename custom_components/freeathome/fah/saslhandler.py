import logging

import sys
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.matcher import MatchXPath
from slixmpp.plugins.xep_0009.binding import py2xml, xml2py, xml2fault, fault2xml
from .crypto import Crypto, loginSaslPayload, buildSaslResponse
from .messagewriter import MessageWriter
from .constants import FAHMessage, General

import base64
from slixmpp.plugins.xep_0009.binding import rpcbase64

log = logging.getLogger(__name__)


class SaslHandler:

    def __init__(self, client, jid, password, iterations, salt):
        self.client = client
        self.x_jid = jid
        self.crypto = Crypto(jid, password, iterations, salt)
        self.crypto.generateKeypair()

    async def initiate_key_exchange(self):

        log.debug('start key exchange')
        key_bytes = self.crypto.generateLocalKey()
        key = base64.b64encode(key_bytes)

        try:
            iq = await self.send_cryptExchangeLocalKeys2(self.x_jid, key)
        except (NameError, ValueError) as e:
            log.error(e)
        except:
            log.error('error send_cryptExchangeLocalKeys2: %s', sys.exc_info()[0])
        else:
            log.debug('crypt_exchange_callback')

            iq.enable('rpc_query')
            if iq['rpc_query']['method_response']['fault'] is not None:
                fault = iq['rpc_query']['method_response']['fault']
                log.info(fault['string'])
            else:
                if iq['rpc_query']['method_response']['params'] is not None:

                    args = xml2py(iq['rpc_query']['method_response']['params'])

                    keymessage = args[0].decode()

                    log.debug('Received Local Key')
                    sessionidentifier = self.crypto.completeKeyExchange(keymessage)

                    payload = self.StartNewSessionPayload(sessionidentifier)
                    log.debug('Sending new session')

                    try:
                        iq = await self.send_cryptMessage(base64.b64encode(payload))
                    except (NameError, ValueError, TypeError) as e:
                        log.error(e)
                    except:
                        log.error('error send_cryptMessage: %s', sys.exc_info()[0])
                    else:
                        iq.enable('rpc_query')

                        if iq['rpc_query']['method_response']['fault'] is not None:
                            fault = iq['rpc_query']['method_response']['fault']
                            log.info(fault['string'])
                        else:
                            if iq['rpc_query']['method_response']['params'] is not None:
                                log.info('Received new session result')

                                args = xml2py(iq['rpc_query']['method_response']['params'])
                                log.info(len(args))

                                newsessionresponse = args[0].decode()

                                log.debug('Received new session response')

                                self.crypto.decodeNewSessionResult(newsessionresponse)  # result is a string + blob

                                scram = self.crypto.clientScramHandler.createClientFirst(self.x_jid)

                                login = loginSaslPayload(scram)
                                payload = self.crypto.encryptPayload(login)

                                log.debug('Sending login sasl')
                                try:
                                    iq = await self.send_cryptMessage(base64.b64encode(payload))
                                except:
                                    log.error('error send_cryptMessage: %s', sys.exc_info()[0])
                                else:

                                    iq.enable('rpc_query')

                                    if iq['rpc_query']['method_response']['fault'] is not None:
                                        fault = iq['rpc_query']['method_response']['fault']
                                        log.info(fault['string'])
                                    else:
                                        if iq['rpc_query']['method_response']['params'] is not None:
                                            log.info('Received response login sasl')

                                        args = xml2py(iq['rpc_query']['method_response']['params'])

                                        saslChallengeResponse = args[0].decode()

                                        saslChallengeMessage = self.crypto.decryptPayload(
                                            saslChallengeResponse)  # returns messageReader object

                                        msgId = saslChallengeMessage.readUint8()
                                        if msgId == FAHMessage.MSG_ID_SASL_CHALLENGE:
                                            log.debug("Received SASL Challenge")

                                            clientFinal = self.crypto.processSaslChallenge(saslChallengeMessage)

                                            saslResponse = buildSaslResponse(clientFinal)
                                            payload = self.crypto.encryptPayload(saslResponse)
                                            log.debug('Sending sasl response')

                                            try:
                                                iq = await self.send_cryptMessage(base64.b64encode(payload))
                                            except:
                                                log.error('error send_cryptMessage: %s', sys.exc_info()[0])
                                            else:
                                                iq.enable('rpc_query')

                                                if iq['rpc_query']['method_response']['fault'] is not None:
                                                    fault = iq['rpc_query']['method_response']['fault']
                                                    log.info(fault['string'])
                                                else:
                                                    if iq['rpc_query']['method_response']['params'] is not None:
                                                        log.info('Received response challenge')

                                                        args = xml2py(iq['rpc_query']['method_response']['params'])

                                                        saslChallengeResponse2 = args[0].decode()

                                                        saslSucces = self.crypto.decryptPayload(saslChallengeResponse2)
                                                        msgId = saslSucces.readUint8()

                                                        if msgId == FAHMessage.MSG_ID_SASL_LOGIN_SUCCESS:
                                                            self.crypto.processSaslFinal(saslSucces)
                                                            log.info("Received SASL Login Confirmation")
                                                            log.info("Successfully Authenticated")
                                        else:
                                            log.info("Wrong response: %s", msgId)

    # First call
    def send_cryptExchangeLocalKeys2(self, jid, key, timeout=None, callback=None, timeout_callback=None):

        rpckey = rpcbase64(key)

        iq = self.client.make_iq_set()
        iq['to'] = 'mrha@busch-jaeger.de/rpc'
        iq['xmlns'] = 'jabber:client'
        # iq['from'] = 'installer@busch-jaeger.de' # self.boundjid.full
        iq.enable('rpc_query')
        iq['rpc_query']['method_call']['method_name'] = 'RemoteInterface.cryptExchangeLocalKeys2'
        iq['rpc_query']['method_call']['params'] = py2xml(jid, rpckey, 'SCRAM-SHA-256', 0)

        return iq.send(timeout=timeout, callback=callback, timeout_callback=timeout_callback)

    # rest of the calls
    def send_cryptMessage(self, message, timeout=None, callback=None, timeout_callback=None):
        rpcmessage = rpcbase64(message)
        iq = self.client.make_iq_set()
        iq['to'] = 'mrha@busch-jaeger.de/rpc'
        iq['from'] = self.client.boundjid.full
        iq.enable('rpc_query')
        iq['rpc_query']['method_call']['method_name'] = 'RemoteInterface.cryptMessage'
        iq['rpc_query']['method_call']['params'] = py2xml(rpcmessage)

        return iq.send(timeout=timeout, callback=callback, timeout_callback=timeout_callback)

    def StartNewSessionPayload(self, sessionIdentifier):
        mes = MessageWriter()
        mes.writeUint8(int(FAHMessage.MSG_ID_NEW_SESSION))
        mes.writeUint32(General.PROTOCOL_VERSION)
        mes.writeUint8(FAHMessage.AUTH_TYPE_USER)
        mes.writeString(sessionIdentifier)
        return mes.toUint8Array()
