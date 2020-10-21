import json
import logging
import aiohttp
import asyncio

log = logging.getLogger(__name__)

async def fetch(session, url):
    async with session.get(url) as response:
         return await response.text()

class SettingsFah:

    def __init__(self, host, filename=None):
        self.data = None
        self.host = host
        self.filename = filename

    async def load_json(self):
        if self.filename is None:
            http = 'http://' + self.host + '/settings.json'
            try:
                async with aiohttp.ClientSession() as session:
                    html = await fetch(session, http)
                    self.data = json.loads(html)
                    return True
            except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
                log.error('server not found')
                return False
        else:
            with open(self.filename, "r") as read_file:
                self.data = json.load(read_file)

    def get_jid(self, name):

        jid = None

        if self.data is not None:
            usernames = self.data['users']
            for key in usernames:
                if key['name'] == name:
                    jid = key['jid']

            if jid is None:
                log.error('user not found')
            else:
                return jid

    def get_flag(self, name):
        flag = None

        if self.data is not None:
            flags = self.data['flags']
            if flags is not None:
                flag = flags[name]

        return flag

    def get_scram_settings(self, name, protocol):
        if self.data is not None:
            usernames = self.data['users']
            for key in usernames:
                if key['name'] == name:
                    authmethods = key['authmethods']
                    scram = authmethods[protocol]
                    return scram['iterations'], scram['salt']
