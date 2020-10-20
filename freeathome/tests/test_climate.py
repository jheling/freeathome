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

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("1004_room_temperature_controller.xml"))
class TestClimate:
    async def test_climate(self, _):
        client = get_client()
        await client.find_devices(True)

        devices = client.get_devices("thermostat")
        assert len(devices) == 1
        climate = next((el for el in devices if el.lookup_key == "ABB700D12345/ch0000"))

        # Test attributes
        assert climate.name == "RTR AB (room1)"
        assert climate.serialnumber == "ABB700D12345"
        assert climate.channel_id == "ch0000"
        assert climate.device_info["identifiers"] == {("freeathome", "ABB700D12345")}
        assert climate.device_info["name"] == "RTR AB (ABB700D12345)"
        assert climate.device_info["model"] == "Raumtemperaturregler"
        assert climate.device_info["sw_version"] == "2.1139"

        # TODO: Convert to decimal
        # TODO: This should be its own sensor
        assert climate.current_temperature == '21.56'
        assert climate.target_temperature == '20'
        # TODO: This should be its own sensor
        assert climate.current_actuator == '16'
        assert climate.state == True
        assert climate.ecomode == False

        # Test datapoints
        await climate.turn_on()
        client.set_datapoint.assert_has_calls([
            call("ABB700D12345", "ch0000", "idp0011", "0"),
            call("ABB700D12345", "ch0000", "idp0012", "1"),
            ])

        client.set_datapoint.reset_mock()
        await climate.turn_off()
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0000", "idp0012", "0")

        client.set_datapoint.reset_mock()
        await climate.eco_mode()
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0000", "idp0011", "2")

        client.set_datapoint.reset_mock()
        await climate.set_target_temperature(22.5)
        client.set_datapoint.assert_called_once_with("ABB700D12345", "ch0000", "idp0016", "22.50")

        # Test changing target temperature
        await client.update_devices(load_fixture("1004_update_target_temperature.xml"))
        assert climate.target_temperature == '20.5'

        # Test updating current temperature
        await client.update_devices(load_fixture("1004_update_current_temperature.xml"))
        assert climate.current_temperature == '20.9'

        # Test eco mode turned on
        await client.update_devices(load_fixture("1004_update_eco_mode.xml"))
        assert climate.ecomode == True

        # Test device turned off
        await client.update_devices(load_fixture("1004_update_turn_off.xml"))
        assert climate.state == False

        # Test device turned back on, target temperature, and actuator value up
        await client.update_devices(load_fixture("1004_update_turn_on.xml"))
        assert climate.state == True
        assert climate.target_temperature == '18'
        assert climate.current_actuator == '27'

        # Test eco mode turned off, and target temperature up
        await client.update_devices(load_fixture("1004_update_eco_mode_off.xml"))
        assert climate.ecomode == False
        assert climate.target_temperature == '21'

        # Test alternative ecomode turn on
        climate.update_datapoint('odp0009', '36')
        assert climate.ecomode == True

        climate.update_datapoint('odp0009', '33')
        assert climate.ecomode == False

    async def test_climate_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)
        devices = client.get_devices("thermostat")
        climate = next((el for el in devices if el.lookup_key == "ABB700D12345/ch0000"))

        assert climate.name == "RTR AB"
