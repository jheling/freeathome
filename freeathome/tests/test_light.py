import pytest
pytestmark = pytest.mark.asyncio

import logging
from async_mock import call,patch, AsyncMock

from fah.pfreeathome import Client
from common import load_fixture

LOG = logging.getLogger(__name__)

def get_client():
    client = Client()
    client.devices = set()
    client.monitored_datapoints = {}
    client.set_datapoint = AsyncMock()

    return client

@pytest.fixture(autouse=True)
def mock_init():
    with patch("fah.pfreeathome.Client.__init__", return_value=None):
        yield

@pytest.fixture(autouse=True)
def mock_roomnames():
    with patch("fah.pfreeathome.get_room_names", return_value={"00":{"00":"room1", "01":"room2"}}):
        yield

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("100C_sensor_actuator_1gang.xml"))
class TestLight:
    async def test_light(self, _):
        client = get_client()
        await client.find_devices(True)

        devices = client.get_devices("light")
        assert len(devices) == 1
        light = next((el for el in devices if el.lookup_key == "ABB700D12345/ch0003"))

        # Test attributes
        assert light.name == "Büro (room1)"
        assert light.serialnumber == "ABB700D12345"
        assert light.channel_id == "ch0003"
        assert light.device_info["identifiers"] == {("freeathome", "ABB700D12345")}
        assert light.device_info["name"] == "Sensor/ Schaltaktor Büro (ABB700D12345)"
        assert light.device_info["model"] == "Sensor/ Schaltaktor 1/1-fach"
        assert light.device_info["sw_version"] == "2.1366"
        assert light.is_on() == True

        # Test datapoints
        await light.turn_on()
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0003", "idp0000", "1")

        client.set_datapoint.reset_mock()
        await light.turn_off()
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0003", "idp0000", "0")

        # Test device being turned off
        await client.update_devices(load_fixture("100C_update_light.xml"))
        assert light.is_on() == False


    async def test_light_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)

        devices = client.get_devices("light")
        assert len(devices) == 1
        light = next((el for el in devices if el.lookup_key == "ABB700D12345/ch0003"))

        assert light.name == "Büro"


@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("B008_sensor_actuator_8gang.xml"))
class TestLight8Gang:
    async def test_light(self, _):
        client = get_client()
        await client.find_devices(True)

        devices = client.get_devices("light")
        assert len(devices) == 6
        light = next((el for el in devices if el.lookup_key == "ABB2E0612345/ch000C"))

        # Test attributes
        assert light.name == "Hinten rechts (room1)"
        assert light.serialnumber == "ABB2E0612345"
        assert light.channel_id == "ch000C"
        assert light.device_info["identifiers"] == {("freeathome", "ABB2E0612345")}
        assert light.device_info["name"] == "Sensor/ Schaltaktor 8/8fach, REG (ABB2E0612345)"
        assert light.device_info["model"] == "Sensor/ Schaltaktor 8/8fach, REG"
        assert light.device_info["sw_version"] == "1.11"
        assert light.is_on() == False

        # Test datapoints
        await light.turn_on()
        client.set_datapoint.assert_called_once_with("ABB2E0612345", "ch000C", "idp0000", "1")

        client.set_datapoint.reset_mock()
        await light.turn_off()
        client.set_datapoint.assert_called_once_with("ABB2E0612345", "ch000C", "idp0000", "0")

        # Test device being turned off
        await client.update_devices(load_fixture("B008_update_light.xml"))
        assert light.is_on() == True


    async def test_light_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)

        devices = client.get_devices("light")
        assert len(devices) == 6
        light = next((el for el in devices if el.lookup_key == "ABB2E0612345/ch000C"))

        assert light.name == "Hinten rechts"

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("hue_dimmer.xml"))
class TestDimmer:
    async def test_dimmer(self, _):
        client = get_client()
        await client.find_devices(True)

        devices = client.get_devices("light")
        assert len(devices) == 1
        light = next((el for el in devices if el.lookup_key == "BEED82AC0001/ch0000"))

        # Test attributes
        assert light.name == "Arbeitsfläche (room1)"
        assert light.serialnumber == "BEED82AC0001"
        assert light.channel_id == "ch0000"
        assert light.device_info["identifiers"] == {("freeathome", "BEED82AC0001")}
        assert light.device_info["name"] == "Arbeitsfläche (BEED82AC0001)"
        assert light.device_info["model"] == "Hue Aktor"
        assert light.device_info["sw_version"] == "123" # ABB dev humor?
        assert light.is_on() == True

        # Test datapoints
        await light.turn_on()
        client.set_datapoint.assert_has_calls([
                call("BEED82AC0001", "ch0000", "idp0000", "1"),
                call("BEED82AC0001", "ch0000", "idp0002", "100"),
                ])

        client.set_datapoint.reset_mock()
        await light.turn_off()
        client.set_datapoint.assert_called_once_with("BEED82AC0001", "ch0000", "idp0000", "0")

        # Set brightness
        client.set_datapoint.reset_mock()
        light.set_brightness('48')
        await light.turn_on()
        client.set_datapoint.assert_has_calls([
                call("BEED82AC0001", "ch0000", "idp0000", "1"),
                call("BEED82AC0001", "ch0000", "idp0002", "48"),
                ])

        # Test device being turned off
        light.update_datapoint('odp0001', '36')
        assert light.get_brightness() == '36'

        # Test device being turned off
        light.update_datapoint('odp0000', '0')
        assert light.is_on() == False


    async def test_light_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)

        devices = client.get_devices("light")
        assert len(devices) == 1
        light = next((el for el in devices if el.lookup_key == "BEED82AC0001/ch0000"))

        assert light.name == "Arbeitsfläche"
