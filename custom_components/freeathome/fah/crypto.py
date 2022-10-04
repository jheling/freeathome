import hashlib
from .pure_pynacl import (
    crypto_onetimeauth_poly1305_tweet as crypto_onetimeauth,
    crypto_onetimeauth_poly1305_tweet_verify as crypto_onetimeauth_verify,
    IntArray,
)
from .pure_pynacl import tweetnacl
from nacl.bindings.crypto_box import crypto_box_keypair
from nacl.hash import generichash
from nacl.utils import random
from nacl.encoding import RawEncoder
from nacl.bindings import (
    crypto_box_NONCEBYTES,
    crypto_box_ZEROBYTES,
    crypto_box_BOXZEROBYTES,
    crypto_secretbox_KEYBYTES,
    crypto_box_beforenm,
    crypto_box_afternm,
    crypto_box_open_afternm,
    crypto_secretbox_open,
)
import logging
import base64
from .messagereader import MessageReader
from .messagewriter import MessageWriter
from .clientscramhandler import ClientScramHandler
from .constants import General, Result, FAHMessage

log = logging.getLogger(__name__)
crypto_box_MACBYTES = crypto_box_ZEROBYTES - crypto_box_BOXZEROBYTES


class Crypto:
    def __init__(self, jid, password, iterations, salt):
        self.jid = jid
        self.password = password
        self.iterations = iterations
        self.salt = base64.b64decode(salt)
        self.__Yq = {}
        self.clientScramHandler = ClientScramHandler()
        self.__Yv = False
        self.messageCounter = 1
        self.__Yp = []

    def generateKeypair(self):
        keypair = crypto_box_keypair()

        self.publicKey = keypair[0]
        self.secretKey = keypair[1]

    # complete
    def generateSharedKey(self):
        return hashlib.pbkdf2_hmac(
            "sha256", bytes(self.password, "utf-8"), self.salt, self.iterations
        )

        # complete

    def generateLocalKey(self):
        sharedKey = self.generateSharedKey()
        buffer = random(16)

        authenticator = self.makeAuthenticator(sharedKey, buffer)

        return authenticator

    # complete
    def makeAuthenticator(self, message, key):

        generic_hash = generichash(data=message, key=key, encoder=RawEncoder)

        if generic_hash is None:
            raise Error("generic hash undefined")

        tok = IntArray(tweetnacl.u8, size=32)
        crypto_onetimeauth(tok, m=self.publicKey, n=len(self.publicKey), k=generic_hash)
        token = bytes(tok[:16])

        if len(self.publicKey) + len(key) + len(token) != 64:
            raise Error("Unexpected token size")

        authenticator = bytearray(self.publicKey)
        authenticator.extend(key)
        authenticator.extend(token)

        return authenticator

    def completeKeyExchange(self, data):

        if len(data) < 8:
            raise Error("Invalid KeyExchange response")

        pos = 0

        keyExchangeVersion = int.from_bytes(data[pos : pos + 4], "little")

        pos += 4
        log.info(keyExchangeVersion)

        if keyExchangeVersion != 2:
            raise Exception("Unexpected KeyExchange version %", keyExchangeVersion)

        errorCode = int.from_bytes(data[pos : pos + 4], "little")
        pos += 4

        if errorCode != 0 and errorCode != 25:
            raise Exception(
                "received error code % as result of KeyExchange ", errorCode
            )

        if len(data) < (pos + 16 + 16):
            raise Exception(
                "Insufficient data length in KeyExchange response, have only % bytes ",
                len(data),
            )

        fD = data[pos : pos + 16]
        pos += 16
        fS = data[pos : pos + 16]
        pos += 16

        sharedKey = self.generateSharedKey()

        authenticatorValid = self.validateAuthenticator(data[pos:], fD, fS, sharedKey)

        if authenticatorValid is None:
            raise Exception("Failed to authenticate key exchange data")

        fK = self.extractData(data, pos)
        pos += fK["length"]
        sessionIdentifier = fK["data"]

        flags = self.extractData(data, pos)
        pos += flags["length"]

        if len(data) < (pos + 32):
            raise Exception(
                "KeyExchange response buffer too short, expected 32 bytes for public key at pos"
                + pos
                + ",have length "
                + len(data)
            )

        publicKey = data[pos : pos + 32]

        self.cryptoIntermediateData = crypto_box_beforenm(publicKey, self.secretKey)

        return sessionIdentifier

    def extractData(self, fX, fY):
        if len(fX) < (fY + 4):
            raise Exception("Cannot read string from buffer, buffer not large enough")

        fW = fX
        length = int.from_bytes(
            fX[fY : (fY + 3)],
            "little",
        )

        if length == 0:
            raise Exception("Failed to read keyId from KeyExchange response")

        if length > 20000000:
            raise Exception(
                "Cannot read string from buffer, string length exceeds allowed maximum size"
            )

        if length > (len(fX) - fY - 4):
            raise Exception("Cannot read string from buffer at pos %", fY)

        result = fX[(fY + 4) : (fY + 4 + length)]

        result_ascii = result.decode("utf-8")

        SystemAccessPointResponse = {"data": result_ascii, "length": 4 + length}

        return SystemAccessPointResponse

    def validateAuthenticator(self, message2, message, token, key):

        keyHash = generichash(data=key, key=message, encoder=RawEncoder)

        if keyHash is None:
            return False

        result = crypto_onetimeauth_verify(token, message2, len(message2), keyHash)

        return result

    # decoding pubsub messages
    def decryptPubSub(self, data):

        data_bytes = base64.b64decode(data)

        if data_bytes is None or len(data_bytes) == 0:
            raise Exception("Can not decrypt empty pubsub")

        nonce = data_bytes[0:crypto_box_NONCEBYTES]

        messageReader = MessageReader(data_bytes[16:24])
        nonceNumber = messageReader.readUint64()
        if "update" not in self.__Yq:
            self.__Yq["update"] = {}
            self.__Yq["update"][
                "sequenceCounter"
            ] = "cU"  # Was this supposed to be cU (without quotes)?
            self.__Yq["update"]["skippedSymmetricSequences"] = []

        sequenceNumber = self.__Yq["update"]["sequenceCounter"]
        if nonceNumber < sequenceNumber:
            if nonceNumber not in self.__Yq["update"]["skippedSymmetricSequences"]:
                raise Exception(
                    "Unexpected sequence in received symmetric nonce ",
                    nonceNumber,
                    "(",
                    sequenceNumber,
                    ")",
                )

            self.__Yq["update"]["skippedSymmetricSequences"].remove(nonceNumber)

        if nonceNumber > sequenceNumber:
            c = nonceNumber - sequenceNumber - 1
            if c > 16:
                c = 16

            x = nonceNumber - 1
            for i in range(c):
                if x == 0:
                    break

            self.__Yq["update"]["skippedSymmetricSequences"].append(x)
            x -= x

            if len(self.__Yq["update"]["skippedSymmetricSequences"]) > 32:
                a = sorted(
                    self.__Yq["update"]["skippedSymmetricSequences"]
                )  # returns list
                dK = len(a) - 32
                for i in range(dK):
                    self.__Yq["update"]["skippedSymmetricSequences"].remove(a[i])

        self.__Yq["update"]["sequenceCounter"] += 1
        pubSubMessage = crypto_secretbox_open(
            data_bytes[crypto_box_NONCEBYTES:], nonce, self.__Key
        )

        if pubSubMessage is None:
            raise Exception("Failed to decrypt message")

        return pubSubMessage

    def decodeNewSessionResult(self, newsession):

        data = MessageReader(newsession)

        got_type = data.readUint8()

        result = data.readUint32()
        if result != Result.RESULT_CODE_OK:
            raise Exception("Failed to establish session")

        fah_version = data.readUint32()
        if fah_version != General.PROTOCOL_VERSION:
            log.info("Unknown Protocol Version detected. Ignoring ...", fah_version)

        self.__Ys = data.readString()
        self.__Yt = data.readBlob(8)

    def createNonce(self):
        cl = MessageWriter()
        cl.writeBlob(self.__Yt)
        cl.writeUint32(self.messageCounter)
        self.messageCounter += 1
        cl.writeUint32(0)

        if self.messageCounter > 4294967296:
            raise Exception("MessageCounter exceeds valid range")

        cl.writeBlob(random(8))
        return cl.toUint8Array()

    def encryptPayload(self, data):
        if len(data) > 10485760:
            raise Exception("encryptPayload: message is too large: ", len(data))

        cq = 0
        if not self.__Yv:
            cq = cq | 2

        nonce = self.createNonce()

        if nonce is None:
            raise Exception("MessageCounter exceeds valid range")

        cn = len(nonce) + General.FH_CRYPTO_MAC_LENGTH + len(data)
        ct = bytearray(random(crypto_box_NONCEBYTES))

        cm = bytearray()
        cm += ct
        cm += data

        cr = crypto_box_afternm(bytes(cm), bytes(nonce), self.cryptoIntermediateData)

        if cr is None or len(cr) == 0:
            raise Exception("Failed to encrypt message")

        if len(cr) != cn:
            raise Exception("Internal error: Unexpected size of encrypted data array")

        self.__Yp.append(ct)  # append random nonce bytes to list

        co = MessageWriter()
        co.writeUint8(FAHMessage.MSG_ID_CRYPTED_CONTAINER_TO_SERVER)
        co.writeUint8(cq)
        co.writeString(self.__Ys)
        co.writeBlob(nonce)
        co.writeUint32(cn)
        co.writeBlob(cr)

        return co.toUint8Array()

    def decryptPayload(self, message):  # data is of type messagereader

        data = MessageReader(message)

        got_type = data.readUint8()

        cs = data.readUint8()
        messageLength = data.readUint32()
        messageData = data.getRemainingData()

        if len(messageData) != messageLength:
            raise Exception(
                "Failed to decrypt container: invalid message length ",
                messageLength,
                " expected ",
                len(messageData),
            )

        if messageLength < crypto_box_MACBYTES:
            raise Exception(
                "Failed to decrypt container: invalid message length ", messageLength
            )

        cX = None

        for x in self.__Yp:
            cX = crypto_box_open_afternm(
                bytes(messageData), bytes(x), self.cryptoIntermediateData
            )

            if cX is not None:
                self.__Yp.remove(x)
                break

        keyData = MessageReader(cX)

        if bool(cs & 2):  # if the keyData contains extra information, then process
            self.__Key = keyData.readBlob(crypto_secretbox_KEYBYTES)
            numNames = keyData.readUint16()

            for i in range(numNames):
                cO = keyData.readString()
                cL = cO.rfind("/")
                if cL == -1:
                    continue

                cR = cO[cL + 1 :]
                if cR.endswith("_encrypted"):
                    cR = cR[0 : len(cR) - 10]

                cU = keyData.readUint64()
                self.__Yq[cR] = {}
                self.__Yq[cR]["sequenceCounter"] = cU
                self.__Yq[cR]["skippedSymmetricSequences"] = []

            self.__Yv = True

        return keyData

    def processSaslChallenge(self, messageReader):
        dq = messageReader.readString()

        self.clientScramHandler.setServerFirst(dq, self.password)

        clientFinal = self.clientScramHandler.createClientFinal()

        if clientFinal is None or len(clientFinal) == 0:
            raise Exception(
                "Failed to send login response message, failed to create clientFinal"
            )

        return clientFinal

    def processSaslFinal(self, messageReader):
        dr = messageReader.readString()

        self.clientScramHandler.setServerFinal(dr)

    def getClientScramHandler(self):
        return self.clientScramHandler


def loginSaslPayload(scram):
    messageWriter = MessageWriter()
    messageWriter.writeUint8(FAHMessage.MSG_ID_LOGIN_SASL)
    messageWriter.writeString("SCRAM-SHA-256")
    messageWriter.writeString(scram)
    return messageWriter.toUint8Array()


def buildSaslResponse(clientFinal):
    messageWriter = MessageWriter()
    messageWriter.writeUint8(FAHMessage.MSG_ID_SASL_RESPONSE)
    messageWriter.writeString(clientFinal)
    return messageWriter.toUint8Array()
