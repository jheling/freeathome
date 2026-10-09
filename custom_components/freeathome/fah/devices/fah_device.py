# Virtual devices, so light groups, scenes and the "all lamps" entry, do not sit
# on the bus. Every SysAP hands out the same FFFF... serial for them, while a
# real device carries a hardware serial that is unique across SysAPs.
VIRTUAL_SERIAL_PREFIX = "FFFF"


class FahDevice:
    """ Free@Home base object """

    def __init__(self, client, device_info, serialnumber, channel_id, function_id, name, datapoints: dict[str, str]={},parameters={}, device_updated_cb=None):
        self._device_info = device_info
        self._serialnumber = serialnumber
        self._channel_id = channel_id
        self._function_id = function_id
        self._name = name
        self._client = client
        self._device_updated_cbs = []
        self._datapoints: dict[str, str] = datapoints
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

    @property
    def unique_id(self):
        """Return the id Home Assistant keeps in the entity registry.

        A hardware serial is unique on its own, so those devices keep the plain
        lookup key, which is what every existing installation already has in
        its registry. A virtual serial repeats on every SysAP, so with more
        than one SysAP the second one would collide with the first and Home
        Assistant would drop its entities. Those get the SysAP in front.

        The device registry is left alone. Two SysAPs still share one device
        entry for their virtual devices, since device_info identifies them by
        the bare serial number. That costs a shared device card, no entity.
        Splitting them as well would need a device registry migration on top.
        """
        if not self.serialnumber.startswith(VIRTUAL_SERIAL_PREFIX):
            return self.lookup_key

        # Falls back to the plain key while no SysAP is set, for example in a
        # test that builds a device without a client.
        sysap_id = getattr(self.client, "sysap_id", "")
        if not sysap_id:
            return self.lookup_key

        return sysap_id + "/" + self.lookup_key
