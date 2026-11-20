import pytest
pytestmark = pytest.mark.asyncio

import os
import logging
from async_mock import patch, AsyncMock

from fah.pfreeathome import Client
from fah.devices.fah_binary_sensor import FahBinarySensor
from fah.const import PID_ADJUST_UP_DOWN
from common import load_fixture, init_client_state


def get_client():
    client = Client()
    client.set_datapoint = AsyncMock()
    client._host = "localhost"
    client.component_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    return client

@pytest.fixture(autouse=True)
def mock_init():
    with patch("fah.pfreeathome.Client.__init__", init_client_state):
        yield

@pytest.fixture(autouse=True)
def mock_roomnames():
    with patch("fah.pfreeathome.get_room_names", return_value={"00":{"00":"room1"}}):
        yield

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("102A_sensor_unit_8gang.xml"))
class TestSensorUnitType7:
    async def test_type7_channels_become_binary_sensors(self, _):
        client = get_client()
        await client.find_devices(True)

        devices = {el.lookup_key: el for el in client.devices}
        assert set(devices) == {"ABB000000102/ch0011", "ABB000000102/ch0026"}
        assert all(isinstance(el, FahBinarySensor) for el in devices.values())

    async def test_unhandled_channel_is_logged(self, _, caplog):
        client = get_client()
        with caplog.at_level(logging.DEBUG, logger="fah.pfreeathome"):
            await client.find_devices(True)

        no_entity = [r.getMessage() for r in caplog.records if r.getMessage().startswith("No entity for")]
        assert no_entity == ["No entity for serialnumber ABB000000102, channel_id ch0015, function ID 229"]

    async def test_rocker_update_records_pairing_id(self, _):
        client = get_client()
        await client.find_devices(True)

        sensor = next(el for el in client.devices if el.lookup_key == "ABB000000102/ch0026")
        events = []

        async def callback(_, event):
            events.append(event)

        sensor.register_datapoint_updated_cb(callback)
        assert sensor.state == "0"

        await client.update_devices(load_fixture("102A_update_rocker.xml"))
        assert sensor.state == "1"
        assert events == [{
                "pid": PID_ADJUST_UP_DOWN,
                "raw_value": "1",
                "command": "pressed",
                "state": True,
                }]
