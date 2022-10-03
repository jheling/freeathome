class FahDevice:
    """ Free@Home base object """

    def __init__(self, client, device_info, serialnumber, channel_id, function_id, name, datapoints={},parameters={}, device_updated_cb=None):
        self._device_info = device_info
        self._serialnumber = serialnumber
        self._channel_id = channel_id
        self._function_id = function_id
        self._name = name
        self._client = client
        self._device_updated_cbs = []
        self._datapoints = datapoints
        self._parameters = parameters
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
    def serialnumber(self):
        """ return the serial number """
        return self._serialnumber

    @property
    def channel_id(self):
        """Return channel id"""
        return self._channel_id

    @property
    def name(self):
        """ return the name of the device   """
        return self._name

    @property
    def client(self):
        """ return the Client object """
        return self._client

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info

    @property
    def lookup_key(self):
        """Return device lookup key"""
        return self.serialnumber + "/" + self.channel_id
