import pytest
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

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("unknown_panel.xml"))
class TestLock:
    async def test_lock(self, _):
        client = get_client()
        await client.find_devices(True)

        devices = client.get_devices("lock")
        assert len(devices) == 1
        lock = next((el for el in devices if el.lookup_key == "ABB654612345/ch0010"))

        # Test attributes
        assert lock.name == "Door opener (room1)"
        assert lock.serialnumber == "ABB654612345"
        assert lock.channel_id == "ch0010"
        assert lock.device_info["identifiers"] == {("freeathome", "ABB654612345")}
        assert lock.device_info["name"] == "Control panel (ABB654612345)"
        assert lock.device_info["model"] == 'free@homeTouch 7"'
        assert lock.device_info["sw_version"] == "0.2.1"
        assert lock.state == '0'

        # Test datapoints
        await lock.lock()
        client.set_datapoint.assert_called_once_with("ABB654612345", "ch0010", "idp0000", "0")

        client.set_datapoint.reset_mock()
        await lock.unlock()
        client.set_datapoint.assert_called_once_with("ABB654612345", "ch0010", "idp0000", "1")

        # Test device being turned off
        await client.update_devices(load_fixture("unknown_update_lock.xml"))
        assert lock.state == '1'


    async def test_lock_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)

        devices = client.get_devices("lock")
        assert len(devices) == 1
        lock = next((el for el in devices if el.lookup_key == "ABB654612345/ch0010"))

        assert lock.name == "Door opener"
