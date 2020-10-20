import pytest
import logging
from async_mock import patch, AsyncMock

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

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("100A_movement_detector_actuator_1gang.xml"))
class TestMovementDetectorLuxSensor:
    async def get_client(self):
        client = Client()
        client.devices = set()
        client.set_datapoint = AsyncMock()

        return client

    async def test_movement_detector_lux_sensor(self, _):
        client = await self.get_client()
        await client.find_devices(True)

        sensor_devices = client.get_devices("sensor")
        assert len(sensor_devices) == 1

        # Test attributes for lux sensor
        sensor = next((el for el in sensor_devices if el.lookup_key == "ABB700C12345/ch0000"))
        assert sensor.name == "Bewegungssensor (room1)_lux"
        assert sensor.serialnumber == "ABB700C12345"
        assert sensor.channel_id == "ch0000"
        assert sensor.device_info["identifiers"] == {("freeathome", "ABB700C12345")}
        assert sensor.device_info["name"] == "Bewegungssensor (ABB700C12345)"
        assert sensor.device_info["model"] == "Bewegungsmelder/Schaltaktor 1-fach"
        assert sensor.device_info["sw_version"] == "2.1366"
        assert sensor.state == "20"

        # Test device event
        await client.update_devices(load_fixture("100A_update_movement_detector.xml"))
        assert sensor.state == "10"
