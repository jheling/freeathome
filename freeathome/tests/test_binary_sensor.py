import pytest
import logging
from async_mock import patch, AsyncMock

from fah.pfreeathome import Client
from common import load_fixture

LOG = logging.getLogger(__name__)

def get_client():
    client = Client()
    client.binary_devices = {}
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
class TestBinarySensors:
    async def test_binary_sensors(self, _):
        client = get_client()
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
        client = get_client()
        await client.find_devices(False)
        sensor = client.binary_devices["ABB700D12345/ch0000"]

        assert sensor.name == "Sensor/ Schaltaktor Büro"

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("100C_sensor_actuator_1gang_splitted.xml"))
class TestBinarySensorsSplitted:
    async def get_client(self):
        client = Client()
        client.binary_devices = {}
        client.set_datapoint = AsyncMock()

        return client

    async def test_binary_sensors(self, _):
        client = await self.get_client()
        await client.find_devices(True)

        assert len(client.binary_devices) == 2

        # Test attributes for top button
        sensor_top = client.binary_devices["ABB700D12345/ch0001"]
        assert sensor_top.name == "Sensor/ Schaltaktor Büro T (room1)"
        assert sensor_top.serialnumber == "ABB700D12345"
        assert sensor_top.channel_id == "ch0001"
        assert sensor_top.output_device == "odp0000"
        assert sensor_top.device_info["identifiers"] == {("freeathome", "ABB700D12345")}
        assert sensor_top.device_info["name"] == "Sensor/ Schaltaktor Büro (ABB700D12345)"
        assert sensor_top.device_info["model"] == "Sensor/ Schaltaktor 1/1-fach"
        assert sensor_top.device_info["sw_version"] == "2.1366"
        assert sensor_top.state == "1"

        # Test device event
        await client.update_devices(load_fixture("100C_update_sensor_splitted.xml"))
        assert sensor_top.state == "0"

        # Test attributes for bottom
        sensor_bottom = client.binary_devices["ABB700D12345/ch0002"]
        assert sensor_bottom.name == "Sensor/ Schaltaktor Büro B (room1)"
        assert sensor_bottom.serialnumber == "ABB700D12345"
        assert sensor_bottom.channel_id == "ch0002"
        assert sensor_bottom.output_device == "odp0000"
        assert sensor_bottom.device_info["identifiers"] == {("freeathome", "ABB700D12345")}
        assert sensor_bottom.device_info["name"] == "Sensor/ Schaltaktor Büro (ABB700D12345)"
        assert sensor_bottom.device_info["model"] == "Sensor/ Schaltaktor 1/1-fach"
        assert sensor_bottom.device_info["sw_version"] == "2.1366"
        assert sensor_bottom.state == "0"


    async def test_sensor_no_room_name(self, _):
        client = await self.get_client()
        await client.find_devices(False)
        sensor_top = client.binary_devices["ABB700D12345/ch0001"]

        assert sensor_top.name == "Sensor/ Schaltaktor Büro T"

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("B008_sensor_actuator_8gang.xml"))
class TestBinarySensors8Gang:
    async def test_binary_sensors(self, _):
        client = get_client()
        await client.find_devices(True)

        assert len(client.binary_devices) == 3

        # Light switch
        sensor = client.binary_devices["ABB2E0612345/ch0000"]

        # Test attributes
        assert sensor.name == "Taster (room1)"
        assert sensor.serialnumber == "ABB2E0612345"
        assert sensor.channel_id == "ch0000"
        assert sensor.output_device == "odp0000"
        assert sensor.device_info["identifiers"] == {("freeathome", "ABB2E0612345")}
        assert sensor.device_info["name"] == "Sensor/ Schaltaktor 8/8fach, REG (ABB2E0612345)"
        assert sensor.device_info["model"] == "Sensor/ Schaltaktor 8/8fach, REG"
        assert sensor.device_info["sw_version"] == "1.11"
        assert sensor.state == "0"

        # Test device event
        await client.update_devices(load_fixture("B008_update_sensor.xml"))
        assert sensor.state == "1"

        # Dimming sensor
        dimming_sensor = client.binary_devices["ABB2E0612345/ch0001"]

        assert dimming_sensor.name == "Dimmsensor (room1)"
        assert dimming_sensor.serialnumber == "ABB2E0612345"
        assert dimming_sensor.channel_id == "ch0001"
        assert dimming_sensor.output_device == "odp0000"
        assert dimming_sensor.state == "0"

        # TODO: Add support for blind sensor

        # Staircase sensor
        staircase_sensor = client.binary_devices["ABB2E0612345/ch0003"]

        assert staircase_sensor.name == "Treppenhauslichtsensor (room1)"
        assert staircase_sensor.serialnumber == "ABB2E0612345"
        assert staircase_sensor.channel_id == "ch0003"
        assert staircase_sensor.output_device == "odp0000"
        assert staircase_sensor.state == "0"

        # TODO: Add support for force position light sensor
        # TODO: Add support for force position cover sensor
        # TODO: Add support for window contact sensor
        # TODO: Add support for movement sensor

    async def test_sensor_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)
        sensor = client.binary_devices["ABB2E0612345/ch0000"]

        assert sensor.name == "Taster"


@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("1013_blind_sensor_actuator_1gang.xml"))
class TestBinarySensorsCover:
    async def test_binary_sensors(self, _):
        client = get_client()
        await client.find_devices(True)

        # Cover sensor does not yield a binary sensor (there is no on/off state)
        assert len(client.binary_devices) == 0
