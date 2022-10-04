import hashlib
from nacl.utils import random
import base64
import hmac
import logging

log = logging.getLogger(__name__)


class ClientScramHandler:
    def createClientFirst(self, text):

        buf = random(32)
        if buf is None or len(buf) != 32:
            raise Exception("Could not generate random bytes")

        N = str(base64.b64encode(buf), "utf-8")
        self.scram = "n,,n=" + text + ",r=" + N

        return self.scram

    def createClientFinal(self):
        clientFinalMessageBare = "c=biws,r=" + self.serverNonce
        self.authmessage = (
            self.scram[3:]
            + ","
            + self.serverChallengeResponse
            + ","
            + clientFinalMessageBare
        )

        clientSignature = self.createClientSignature(self.clientKey)
        if clientSignature is None:
            raise Exception("Failed to create client signature")

        clientSignature = self.byte_xor(clientSignature, self.clientKey)

        Q = str(base64.b64encode(clientSignature), "utf-8")
        clientFinalMessageBare += ",p=" + Q
        return clientFinalMessageBare

    def byte_xor(self, ba1, ba2):
        return bytes([_a ^ _b for _a, _b in zip(ba1, ba2)])

    def setServerFirst(self, response, password):
        self.serverChallengeResponse = response

        self.serverNonce = self.searchItem(self.serverChallengeResponse, "r")

        salt_string = self.searchItem(self.serverChallengeResponse, "s")

        iteration_string = self.searchItem(self.serverChallengeResponse, "i")

        if (
            len(self.serverNonce) == 0
            or len(salt_string) == 0
            or len(iteration_string) == 0
        ):
            raise Exception("Missing one or more parameters in SCRAM-SHA challenge")

        if len(salt_string) < 32:
            raise Exception("setServerFirst: salt is too short")

        self.iterations = int(iteration_string)
        if (
            self.iterations is None
            or self.iterations < 4096
            or self.iterations > 600000
        ):
            raise Exception("Invalid iteration parameter in SCRAM-SHA challenge")

        self.salt = base64.b64decode(salt_string)
        if self.salt is None or len(self.salt) < 32:
            raise Exception("Failed to decode s parameter of SCRAM-SHA challenge")

        self.clientKey = self.createClientKey(password)
        if self.clientKey is None or len(self.clientKey) == 0:
            raise Exception("Failed to create clientKey")

        self.serverKey = self.createServerKey(password)
        if self.serverKey is None or len(self.serverKey) == 0:
            raise Exception("Failed to create serverKey")

    def setServerFinal(self, X):

        Y = bytes(self.searchItem(X, "v"), "utf-8")
        if Y == "":
            raise Exception("setServerFinal: Missing v parameter")

        bb = hmac.new(
            self.serverKey, bytes(self.authmessage, "utf-8"), digestmod=hashlib.sha256
        ).digest()
        if bb is None or len(bb) <= 0:
            raise Exception("setServerFinal: Failed to calculate HMAC")

        ba = base64.b64encode(bb)

        if Y != ba:
            raise Exception("Failed to verify server SCRAM-SHA signature")

    def searchItem(self, scram_string, id_name):
        if len(scram_string) < 2:
            return ""

        if scram_string[0] == id_name and scram_string[1] == "=":
            bc = 0
        else:
            bc = scram_string.find("," + id_name + "=")
            if bc == -1:
                return ""

            bc += 1

        bd = scram_string.find(",", bc)
        if bd == -1:
            bd = len(scram_string)

        return scram_string[bc + 2 : bd]

    def createClientKey(self, password):
        bj = hashlib.pbkdf2_hmac(
            "sha256", bytes(password, "utf8"), self.salt, self.iterations
        )
        if bj is None or len(bj) <= 0:
            raise Exception("__createClientKey: PBKDF2_HMAC_SHA256 failed")

        bi = "Client Key".encode()
        bg = hmac.new(bj, bi, digestmod=hashlib.sha256).digest()

        if bg is None or len(bg) <= 0:
            raise Exception("__createClientKey: HMAC failed")

        return bg

    def createServerKey(self, password):
        bn = hashlib.pbkdf2_hmac(
            "sha256", bytes(password, "utf8"), self.salt, self.iterations
        )
        if bn is None or len(bn) <= 0:
            raise Exception("__createServerKey: PBKDF2_HMAC_SHA256 failed")

        bm = "Server Key".encode()
        bk = hmac.new(bn, bm, digestmod=hashlib.sha256).digest()

        if bk is None or len(bk) <= 0:
            raise Exception("__createServerKey: HMAC failed")

        return bk

    def createClientSignature(self, bq):
        bp = hashlib.sha256(bq).digest()
        bo = hmac.new(
            bp, bytes(self.authmessage, "utf8"), digestmod=hashlib.sha256
        ).digest()
        if bo is None or len(bo) <= 0:
            raise Exception("Failed to create client signature")

        return bo
