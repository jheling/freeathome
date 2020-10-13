import pytest
import logging
from async_mock import patch, AsyncMock

from fah.pfreeathome import Client
from common import load_fixture

LOG = logging.getLogger(__name__)

@pytest.fixture
def client():
    return Client()

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
    async def get_client(self):
        client = Client()
        client.get_datapoint = AsyncMock()
        client.set_datapoint = AsyncMock()

        return client

    async def test_light(self, _):
        client = await self.get_client()
        await client.find_devices(True)

        assert len(client.light_devices) == 1
        light = client.light_devices["ABB700D12345/ch0003"]

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

    async def test_light_no_room_name(self, _):
        client = await self.get_client()
        await client.find_devices(False)
        light = client.light_devices["ABB700D12345/ch0003"]

        assert light.name == "Büro"
