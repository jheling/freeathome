import pytest
import logging
from async_mock import call,patch, AsyncMock

from fah.pfreeathome import Client
from common import load_fixture

LOG = logging.getLogger(__name__)

def get_client():
    client = Client()
    client.devices = {}
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

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("scene.xml"))
class TestLight:
    async def test_scene(self, _):
        client = get_client()
        await client.find_devices(True)

        assert len(client.get_devices("scene")) == 2

        # First scene
        scene = client.get_devices("scene")["FFFF4800000F/ch0000"]

        # Test attributes
        assert scene.name == "Eigene Szene (room1)"
        assert scene.serialnumber == "FFFF4800000F"
        assert scene.channel_id == "ch0000"
        assert scene.device_info["identifiers"] == {("freeathome", "FFFF4800000F")}
        assert scene.device_info["name"] == "Neue Szene (FFFF4800000F)"
        assert scene.device_info["model"] == "Neue Szene"
        assert scene.device_info["sw_version"] == "0.1"

        # Test datapoints
        await scene.activate()
        client.set_datapoint.assert_called_once_with("FFFF4800000F", "ch0000", "odp0000", "1")

        client.set_datapoint.reset_mock()

        # First scene
        scene2 = client.get_devices("scene")["FFFF48010001/ch0000"]

        # Test attributes
        assert scene2.name == "Panikszene (room1)"
        assert scene2.serialnumber == "FFFF48010001"
        assert scene2.channel_id == "ch0000"
        assert scene2.device_info["identifiers"] == {("freeathome", "FFFF48010001")}
        assert scene2.device_info["name"] == "Panikszene (FFFF48010001)"
        assert scene2.device_info["model"] == "Panikszene"
        assert scene2.device_info["sw_version"] == "0.1"

        # Test datapoints
        await scene2.activate()
        client.set_datapoint.assert_called_once_with("FFFF48010001", "ch0000", "odp0000", "1")
        client.set_datapoint.reset_mock()

    async def test_scene_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)
        scene = client.get_devices("scene")["FFFF4800000F/ch0000"]

        assert scene.name == "Eigene Szene"
