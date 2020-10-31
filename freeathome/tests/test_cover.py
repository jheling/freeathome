import pytest
import logging
from async_mock import call, patch, AsyncMock

from fah.pfreeathome import Client
from common import load_fixture

LOG = logging.getLogger(__name__)

def get_client():
    client = Client()
    client.devices = set()
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

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("1013_blind_sensor_actuator_1gang.xml"))
class TestCover:
    @pytest.mark.asyncio
    async def test_cover(self, _):
        client = get_client()
        await client.find_devices(True)

        devices = client.get_devices("cover")
        assert len(client.get_devices("cover")) == 1
        cover = next((el for el in devices if el.lookup_key == "ABB700D12345/ch0003"))

        # Test attributes
        assert cover.name == "Gäste-WC (room1)"
        assert cover.serialnumber == "ABB700D12345"
        assert cover.channel_id == "ch0003"
        assert cover.device_info["identifiers"] == {("freeathome", "ABB700D12345")}
        assert cover.device_info["name"] == "Sensor/ Jalousieaktor 1/1-fach (ABB700D12345)"
        assert cover.device_info["model"] == "Sensor/ Jalousieaktor 1/1-fach"
        assert cover.device_info["sw_version"] == "2.1366"

        # TODO: Convert to int, make this a getter
        # TODO: This should return 73, reverse values in component
        assert cover.position == "27"
        assert cover.forced_position == "0"
        assert cover.state == "1"
        assert cover.is_cover_closed() == True
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == False

        # Test datapoints
        await cover.open_cover()
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0003", "idp0000", "0")

        client.set_datapoint.reset_mock()
        await cover.close_cover()
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0003", "idp0000", "1")

        client.set_datapoint.reset_mock()
        # Simulate cover moving
        cover.state = '2'
        await cover.stop_cover()
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0003", "idp0001", "1")

        client.set_datapoint.reset_mock()
        await cover.set_cover_position(41)
        # TODO: This should set 41, reverse in component
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0003", "idp0002", "59")

        client.set_datapoint.reset_mock()
        await cover.set_forced_cover_position(1)
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0003", "idp0004", "1")

        # Status updates
        await client.update_devices(load_fixture("1013_update_closing.xml"))
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == True

        await client.update_devices(load_fixture("1013_update_closed.xml"))
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == False
        assert cover.is_cover_closed() == True
        # TODO: This should return 100, reverse values in component
        assert cover.position == "0"

        await client.update_devices(load_fixture("1013_update_opening.xml"))
        assert cover.is_cover_opening() == True
        assert cover.is_cover_closing() == False

        await client.update_devices(load_fixture("1013_update_open.xml"))
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == False
        assert cover.is_cover_closed() == False
        # TODO: This should return 64, reverse values in component
        assert cover.position == "36"

        await client.update_devices(load_fixture("1013_update_force_opening.xml"))
        assert cover.is_cover_opening() == True
        assert cover.is_cover_closing() == False
        assert cover.is_cover_closed() == False
        assert cover.get_forced_cover_position() == 2

        await client.update_devices(load_fixture("1013_update_force_open_disabled.xml"))
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == True
        assert cover.is_cover_closed() == False
        assert cover.get_forced_cover_position() == 0


    @pytest.mark.asyncio
    async def test_light_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)
        devices = client.get_devices("cover")
        cover = next((el for el in devices if el.lookup_key == "ABB700D12345/ch0003"))

        assert cover.name == "Gäste-WC"
