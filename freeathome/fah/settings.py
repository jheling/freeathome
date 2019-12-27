import urllib.request
import json


class SettingsFah:

    def __init__(self, host, filename=None):
        self.data = None

        if filename is None:
            http = 'http://' + host + '/settings.json'
            try:
                with urllib.request.urlopen(http) as url:
                    self.data = json.loads(url.read().decode())

            except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
                print('server not found')
        else:
            with open(filename, "r") as read_file:
                self.data = json.load(read_file)

    def get_jid(self, name):

        jid = None

        if self.data is not None:
            usernames = self.data['users']
            for key in usernames:
                if key['name'] == name:
                    jid = key['jid']

            if jid is None:
                print('user not found')
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
