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
class TestBinarySensors:
    async def get_client(self):
        client = Client()
        client.set_datapoint = AsyncMock()

        return client

    async def test_binary_sensors(self, _):
        client = await self.get_client()
        await client.find_devices(True)

        assert len(client.binary_devices) == 1
        sensor = client.binary_devices["ABB700D12345/ch0000"]

        # Test attributes
        assert sensor.name == "Sensor/ Schaltaktor Büro (room1)"
        assert sensor.serialnumber == "ABB700D12345"
        assert sensor.channel_id == "ch0000"
        assert sensor.output_device == "odp0000"
        assert sensor.device_info["identifiers"] == {("freeathome", "ABB700D12345")}
        assert sensor.device_info["name"] == "Sensor/ Schaltaktor Büro (ABB700D12345)"
        assert sensor.device_info["model"] == "Sensor/ Schaltaktor 1/1-fach"
        assert sensor.device_info["sw_version"] == "2.1366"
        assert sensor.state == "1"

        # Test device event
        await client.update_devices(load_fixture("100C_update_sensor.xml"))
        assert sensor.state == "0"


    async def test_sensor_no_room_name(self, _):
        client = await self.get_client()
        await client.find_devices(False)
        sensor = client.binary_devices["ABB700D12345/ch0000"]

        assert sensor.name == "Sensor/ Schaltaktor Büro"
