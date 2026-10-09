"""Tests for free@home trigger channels."""

import os

import pytest

from async_mock import AsyncMock, call, patch
from common import init_client_state, load_fixture
from fah.pfreeathome import Client

pytestmark = pytest.mark.asyncio

def get_client():
    """Return a minimally mocked free@home client."""
    client = Client()
    client.set_datapoint = AsyncMock()
    client._host = "localhost"
    client.component_path = os.path.dirname(
        os.path.dirname(os.path.dirname(__file__))
    )
    return client


@pytest.fixture(autouse=True)
def mock_init():
    """Skip the network client initialization."""
    with patch("fah.pfreeathome.Client.__init__", new=init_client_state):
        yield


@pytest.fixture(autouse=True)
def mock_roomnames():
    """Provide one deterministic room name."""
    with patch(
        "fah.pfreeathome.get_room_names",
        return_value={"00": {"00": "room1"}},
    ):
        yield


@patch(
    "fah.pfreeathome.Client.get_config",
    return_value=load_fixture("0045_trigger.xml"),
)
@pytest.mark.parametrize("switch_as_x", [False, True])
async def test_trigger_uses_timed_start_stop(_, switch_as_x):
    """A FID_TRIGGER is a button using AL_TIMED_START_STOP."""
    client = get_client()
    await client.find_devices(True, switch_as_x=switch_as_x)

    triggers = client.get_devices("button")
    assert len(triggers) == 1
    trigger = triggers[0]
    assert trigger.lookup_key == "ABB000000001/ch0003"
    assert client.get_devices("switch") == []
    assert client.get_devices("light") == []
    assert trigger.name == "Timed trigger (room1)"
    assert trigger.unique_id == "ABB000000001/ch0003"
    assert trigger.device_info["identifiers"] == {("freeathome", "ABB000000001")}

    await trigger.press()
    client.set_datapoint.assert_awaited_once_with(
        "ABB000000001", "ch0003", "idp0001", "1"
    )


@pytest.mark.parametrize("switch_as_x", [False, True])
async def test_trigger_and_normal_switch_channels(switch_as_x):
    """A mixed actuator keeps normal channels separate from the trigger."""
    client = get_client()
    with patch.object(Client, "get_config", return_value=load_fixture("B008_sensor_actuator_8gang.xml")):
        await client.find_devices(False, switch_as_x=switch_as_x)

    triggers = client.get_devices("button")
    assert len(triggers) == 1
    assert triggers[0].lookup_key == "ABB2E0612345/ch0012"
    assert len(client.get_devices("switch" if switch_as_x else "light")) == 5
    assert client.get_devices("light" if switch_as_x else "switch") == []
    await triggers[0].press()
    client.set_datapoint.assert_awaited_once_with(
        "ABB2E0612345", "ch0012", "idp0001", "1"
    )


async def test_trigger_requires_timed_datapoint():
    """Do not expose a button when its command datapoint is missing."""
    client = get_client()
    xml = load_fixture("0045_trigger.xml").replace('pairingId="0002"', 'pairingId="FFFF"')
    with patch.object(Client, "get_config", return_value=xml):
        await client.find_devices(False)
    assert client.get_devices("button") == []
    client.set_datapoint.assert_not_awaited()


async def test_trigger_repeated_presses_and_command_failure():
    """Each press sends one pulse, and communication failures reach the caller."""
    client = get_client()
    with patch.object(Client, "get_config", return_value=load_fixture("0045_trigger.xml")):
        await client.find_devices(False)
    trigger = client.get_devices("button")[0]
    await trigger.press()
    await trigger.press()
    assert client.set_datapoint.await_args_list == [
        call("ABB000000001", "ch0003", "idp0001", "1"),
        call("ABB000000001", "ch0003", "idp0001", "1"),
    ]
    client.set_datapoint.reset_mock()
    client.set_datapoint.side_effect = ConnectionError("Disconnected")
    with pytest.raises(ConnectionError, match="Disconnected"):
        await trigger.press()
    client.set_datapoint.assert_awaited_once_with(
        "ABB000000001", "ch0003", "idp0001", "1"
    )
