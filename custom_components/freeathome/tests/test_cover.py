import pytest
pytestmark = pytest.mark.asyncio

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
        assert cover.tilt_position == None
        assert cover.get_forced_cover_position() == "none"
        assert cover.state == "1"
        assert cover.is_cover_closed() == False
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == False

        assert cover.supports_position() == True
        assert cover.supports_tilt_position() == False
        assert cover.supports_forced_position() == True

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
        await cover.set_forced_cover_position("none")
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
        assert cover.get_forced_cover_position() == "open"

        await client.update_devices(load_fixture("1013_update_force_open_disabled.xml"))
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == True
        assert cover.is_cover_closed() == False
        assert cover.get_forced_cover_position() == "none"


    async def test_light_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)
        devices = client.get_devices("cover")
        cover = next((el for el in devices if el.lookup_key == "ABB700D12345/ch0003"))

        assert cover.name == "Gäste-WC"


@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("0109_cover_without_set_position.xml"))
class TestCoverWithoutSetPosition:
    async def test_cover_without_set_position(self, _):
        client = get_client()
        await client.find_devices(False)

        devices = client.get_devices("cover")
        assert len(client.get_devices("cover")) == 1
        cover = next((el for el in devices if el.lookup_key == "ABB5000ABCDE/ch0000"))

        # Test attributes
        assert cover.name == "Cover"
        assert cover.serialnumber == "ABB5000ABCDE"
        assert cover.channel_id == "ch0000"
        assert cover.device_info["identifiers"] == {("freeathome", "ABB5000ABCDE")}
        assert cover.device_info["name"] == "2CSYE1105 (ABB5000ABCDE)"
        assert cover.device_info["model"] == "2CSYE1105"
        assert cover.device_info["sw_version"] == "1.51"

        assert cover.position == None
        assert cover.forced_position == None
        assert cover.state == "1"
        assert cover.is_cover_closed() == None
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == False

        assert cover.supports_position() == False
        assert cover.supports_tilt_position() == False
        assert cover.supports_forced_position() == False

        # Test datapoints
        await cover.open_cover()
        client.set_datapoint.assert_called_once_with("ABB5000ABCDE", "ch0000", "idp0000", "0")

        client.set_datapoint.reset_mock()
        await cover.close_cover()
        client.set_datapoint.assert_called_once_with("ABB5000ABCDE", "ch0000", "idp0000", "1")

        client.set_datapoint.reset_mock()
        # Simulate cover moving
        cover.state = '2'
        await cover.stop_cover()
        client.set_datapoint.assert_called_once_with("ABB5000ABCDE", "ch0000", "idp0001", "1")

        # Status updates
        await client.update_devices(load_fixture("0109_update_closing.xml"))
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == True
        assert cover.is_cover_closed() == None

        await client.update_devices(load_fixture("0109_update_closed.xml"))
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == False
        assert cover.is_cover_closed() == None

        await client.update_devices(load_fixture("0109_update_opening.xml"))
        assert cover.is_cover_opening() == True
        assert cover.is_cover_closing() == False
        assert cover.is_cover_closed() == None

        await client.update_devices(load_fixture("0109_update_open.xml"))
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == False
        assert cover.is_cover_closed() == None

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("1013_shutter_sensor_actuator_1gang.xml"))
class TestShutter:
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
        assert cover.tilt_position == "28"
        assert cover.get_forced_cover_position() == "none"
        assert cover.state == "1"
        assert cover.is_cover_closed() == False
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == False

        assert cover.supports_position() == True
        assert cover.supports_tilt_position() == True
        assert cover.supports_forced_position() == True

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
        await cover.set_cover_tilt_position(34)
        # TODO: This should set 41, reverse in component
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0003", "idp0003", "66")

        client.set_datapoint.reset_mock()
        await cover.set_forced_cover_position("none")
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

        await client.update_devices(load_fixture("1013_update_tilt_open.xml"))
        assert cover.position == "36"
        # TODO: This should return 0, reverse values in component
        assert cover.tilt_position == "100"

        await client.update_devices(load_fixture("1013_update_tilt_closed.xml"))
        assert cover.position == "36"
        # TODO: This should return 100, reverse values in component
        assert cover.tilt_position == "0"

        await client.update_devices(load_fixture("1013_update_force_opening.xml"))
        assert cover.is_cover_opening() == True
        assert cover.is_cover_closing() == False
        assert cover.is_cover_closed() == False
        assert cover.get_forced_cover_position() == "open"

        await client.update_devices(load_fixture("1013_update_force_open_disabled.xml"))
        assert cover.is_cover_opening() == False
        assert cover.is_cover_closing() == True
        assert cover.is_cover_closed() == False
        assert cover.get_forced_cover_position() == "none"


