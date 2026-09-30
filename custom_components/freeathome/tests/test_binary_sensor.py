import pytest
pytestmark = pytest.mark.asyncio

import os
import logging
from async_mock import patch, AsyncMock

from fah.pfreeathome import Client
from fah.devices.fah_binary_sensor import FahBinarySensor, CYCLIC_PERIOD
from fah.const import (
        PID_RELATIVE_SET_VALUE,
        PID_SWITCH_ON_OFF,
        PID_PRESENCE,
        PID_FIRE_ALARM_ACTIVE,
        PID_WINDOW_DOOR_POSITION,
        )
from fah_event import (
        DIMMING_STATUS_DEFAULT,
        DIMMING_STATUS_OPTIONS,
        create_event_data,
        dimming_status_from_event,
        dimming_status_sequence_from_event,
        )
from common import load_fixture, init_client_state

LOG = logging.getLogger(__name__)

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
    with patch("fah.pfreeathome.get_room_names", return_value={"00":{"00":"room1", "01":"room2"}}):
        yield

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("100C_sensor_actuator_1gang.xml"))
class TestBinarySensors:
    async def test_binary_sensors(self, _):
        client = get_client()
        await client.find_devices(True)

        sensor_devices = client.get_devices("binary_sensor")
        assert len(sensor_devices) == 1

        sensor = next((el for el in sensor_devices if el.lookup_key == "ABB700D12345/ch0000"))

        # Test attributes
        assert sensor.name == "Sensor/ Schaltaktor Büro (room1)"
        assert sensor.serialnumber == "ABB700D12345"
        assert sensor.channel_id == "ch0000"
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

        sensor_devices = client.get_devices("binary_sensor")
        sensor = next((el for el in sensor_devices if el.lookup_key == "ABB700D12345/ch0000"))

        assert sensor.name == "Sensor/ Schaltaktor Büro"

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("100C_sensor_actuator_1gang_splitted.xml"))
class TestBinarySensorsSplitted:
    async def get_client(self):
        client = Client()
        client.devices = set()
        client.set_datapoint = AsyncMock()
        client._host = "localhost"
        client.component_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        return client


    async def test_binary_sensors(self, _):
        client = await self.get_client()
        await client.find_devices(True)

        sensor_devices = client.get_devices("binary_sensor")
        assert len(sensor_devices) == 2

        # Test attributes for top button
        sensor_top = next((el for el in sensor_devices if el.lookup_key == "ABB700D12345/ch0001"))
        assert sensor_top.name == "Sensor/ Schaltaktor Büro T (room1)"
        assert sensor_top.serialnumber == "ABB700D12345"
        assert sensor_top.channel_id == "ch0001"
        assert sensor_top.device_info["identifiers"] == {("freeathome", "ABB700D12345")}
        assert sensor_top.device_info["name"] == "Sensor/ Schaltaktor Büro (ABB700D12345)"
        assert sensor_top.device_info["model"] == "Sensor/ Schaltaktor 1/1-fach"
        assert sensor_top.device_info["sw_version"] == "2.1366"
        assert sensor_top.state == "1"

        # Test device event
        await client.update_devices(load_fixture("100C_update_sensor_splitted.xml"))
        assert sensor_top.state == "0"

        # Test attributes for bottom
        sensor_bottom = next((el for el in sensor_devices if el.lookup_key == "ABB700D12345/ch0002"))
        assert sensor_bottom.name == "Sensor/ Schaltaktor Büro B (room1)"
        assert sensor_bottom.serialnumber == "ABB700D12345"
        assert sensor_bottom.channel_id == "ch0002"
        assert sensor_bottom.device_info["identifiers"] == {("freeathome", "ABB700D12345")}
        assert sensor_bottom.device_info["name"] == "Sensor/ Schaltaktor Büro (ABB700D12345)"
        assert sensor_bottom.device_info["model"] == "Sensor/ Schaltaktor 1/1-fach"
        assert sensor_bottom.device_info["sw_version"] == "2.1366"
        assert sensor_bottom.state == "0"


    async def test_sensor_no_room_name(self, _):
        client = await self.get_client()
        await client.find_devices(False)
        sensor_devices = client.get_devices("binary_sensor")
        sensor_top = next((el for el in sensor_devices if el.lookup_key == "ABB700D12345/ch0001"))

        assert sensor_top.name == "Sensor/ Schaltaktor Büro T"

@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("B008_sensor_actuator_8gang.xml"))
class TestBinarySensors8Gang:
    async def test_binary_sensors(self, _):
        client = get_client()
        await client.find_devices(True)

        sensor_devices = client.get_devices("binary_sensor")
        assert len(sensor_devices) == 8

        # Light switch
        sensor = next((el for el in sensor_devices if el.lookup_key == "ABB2E0612345/ch0000"))

        # Test attributes
        assert sensor.name == "Taster (room1)"
        assert sensor.serialnumber == "ABB2E0612345"
        assert sensor.channel_id == "ch0000"
        assert sensor.device_info["identifiers"] == {("freeathome", "ABB2E0612345")}
        assert sensor.device_info["name"] == "Sensor/ Schaltaktor 8/8fach, REG (ABB2E0612345)"
        assert sensor.device_info["model"] == "Sensor/ Schaltaktor 8/8fach, REG"
        assert sensor.device_info["sw_version"] == "1.11"
        assert sensor.state == "0"

        # Test device event
        await client.update_devices(load_fixture("B008_update_sensor.xml"))
        assert sensor.state == "1"

        # Dimming sensor
        dimming_sensor = next((el for el in sensor_devices if el.lookup_key == "ABB2E0612345/ch0001"))

        assert dimming_sensor.name == "Dimmsensor (room1)"
        assert dimming_sensor.serialnumber == "ABB2E0612345"
        assert dimming_sensor.channel_id == "ch0001"
        assert dimming_sensor.state == "0"
        assert dimming_sensor.supports_dimming_status()

        events = []

        async def callback(_, event):
            events.append(event)

        dimming_sensor.register_datapoint_updated_cb(callback)
        await client.update_devices(load_fixture("B008_update_dimming_sensor.xml"))
        assert events == [{
                "pid": PID_RELATIVE_SET_VALUE,
                "raw_value": "9",
                "command": "dim_start",
                "direction": "up",
                }]

        # Dimming sensor
        dimming_sensor = next((el for el in sensor_devices if el.lookup_key == "ABB2E0612345/ch0002"))

        assert dimming_sensor.name == "Jalousiesensor (room1)"
        assert dimming_sensor.serialnumber == "ABB2E0612345"
        assert dimming_sensor.channel_id == "ch0002"
        assert dimming_sensor.state == "0"


        # Staircase sensor
        staircase_sensor = next((el for el in sensor_devices if el.lookup_key == "ABB2E0612345/ch0003"))

        assert staircase_sensor.name == "Treppenhauslichtsensor (room1)"
        assert staircase_sensor.serialnumber == "ABB2E0612345"
        assert staircase_sensor.channel_id == "ch0003"
        assert staircase_sensor.state == "0"

        # Force position sensor
        staircase_sensor = next((el for el in sensor_devices if el.lookup_key == "ABB2E0612345/ch0004"))

        assert staircase_sensor.name == "Sensor Zwangsstellung Ein/Aus (room1)"
        assert staircase_sensor.serialnumber == "ABB2E0612345"
        assert staircase_sensor.channel_id == "ch0004"
        assert staircase_sensor.state == "0"

        # Cover force position sensor
        cover_force_position_sensor = next((el for el in sensor_devices if el.lookup_key == "ABB2E0612345/ch0005"))

        assert cover_force_position_sensor.name == "Jalousiezwangsstellung (room1)"
        assert cover_force_position_sensor.serialnumber == "ABB2E0612345"
        assert cover_force_position_sensor.channel_id == "ch0005"
        assert cover_force_position_sensor.state == "0"

        # Window contact sensor
        window_contact_sensor = next((el for el in sensor_devices if el.lookup_key == "ABB2E0612345/ch0006"))

        assert window_contact_sensor.name == "Fensterkontakt (room1)"
        assert window_contact_sensor.serialnumber == "ABB2E0612345"
        assert window_contact_sensor.channel_id == "ch0006"
        assert window_contact_sensor.state == "0"

        # Movement sensor
        movement_sensor = next((el for el in sensor_devices if el.lookup_key == "ABB2E0612345/ch0007"))

        assert movement_sensor.name == "Bewegungsmelder-Sensor (room1)"
        assert movement_sensor.serialnumber == "ABB2E0612345"
        assert movement_sensor.channel_id == "ch0007"
        assert movement_sensor.state == "0"


    async def test_sensor_no_room_name(self, _):
        client = get_client()
        await client.find_devices(False)
        sensor_devices = client.get_devices("binary_sensor")
        sensor = next((el for el in sensor_devices if el.lookup_key == "ABB2E0612345/ch0000"))

        assert sensor.name == "Taster"


@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("100A_movement_detector_actuator_1gang.xml"))
class TestMovementDetector:
    async def get_client(self):
        client = Client()
        client.devices = set()
        client.set_datapoint = AsyncMock()
        client._host = "localhost"
        client.component_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        return client


    async def test_movement_detector(self, _):
        client = await self.get_client()
        await client.find_devices(True)

        sensor_devices = client.get_devices("binary_sensor")
        assert len(sensor_devices) == 1

        # Test attributes for top button
        sensor_top = next((el for el in sensor_devices if el.lookup_key == "ABB700C12345/ch0000"))
        assert sensor_top.name == "Bewegungssensor (room1)"
        assert sensor_top.serialnumber == "ABB700C12345"
        assert sensor_top.channel_id == "ch0000"
        assert sensor_top.device_info["identifiers"] == {("freeathome", "ABB700C12345")}
        assert sensor_top.device_info["name"] == "Bewegungssensor (ABB700C12345)"
        assert sensor_top.device_info["model"] == "Bewegungsmelder/Schaltaktor 1-fach"
        assert sensor_top.device_info["sw_version"] == "2.1366"
        assert sensor_top.state == "1"

        # Test device event
        await client.update_devices(load_fixture("100A_update_movement_detector.xml"))
        assert sensor_top.state == "0"


@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("1013_blind_sensor_actuator_1gang.xml"))
class TestBinarySensorsCover:
    async def test_binary_sensors(self, _):
        client = get_client()
        await client.find_devices(True)

        # Cover sensor yields a binary sensor, although it has a limited function
        # (off when moving up, on when moving down)
        sensor_devices = client.get_devices("binary_sensor")
        assert len(sensor_devices) == 1

        # Test attributes for top button
        sensor_cover = next((el for el in sensor_devices if el.lookup_key == "ABB700D12345/ch0000"))
        assert sensor_cover.name == "Sensor/ Jalousieaktor 1/1-fach (room1)"
        assert sensor_cover.serialnumber == "ABB700D12345"
        assert sensor_cover.channel_id == "ch0000"
        assert sensor_cover.device_info["identifiers"] == {("freeathome", "ABB700D12345")}
        assert sensor_cover.device_info["name"] == "Sensor/ Jalousieaktor 1/1-fach (ABB700D12345)"
        assert sensor_cover.device_info["model"] == "Sensor/ Jalousieaktor 1/1-fach"
        assert sensor_cover.device_info["sw_version"] == "2.1366"
        assert sensor_cover.state == "1"


class TestCyclicRepeatFilter:
    """Cyclic keep-alive repetitions must not be reported as new events."""

    def make_sensor(self, datapoints):
        return FahBinarySensor(
                None, {}, "ABB700D12345", "ch0000", "0001", "Sensor", datapoints)

    async def test_cyclic_repeat_is_ignored(self):
        sensor = self.make_sensor({PID_PRESENCE: "odp0001"})

        with patch("fah.devices.fah_binary_sensor.time.monotonic", return_value=1000.0):
            sensor.update_datapoint("odp0001", "1")
        assert sensor.state == "1"

        # Home Assistant resets the sensor after the movement has ended
        sensor.state = "0"

        # Exactly one cycle later, the same value arrives again
        with patch("fah.devices.fah_binary_sensor.time.monotonic",
                   return_value=1000.0 + CYCLIC_PERIOD):
            sensor.update_datapoint("odp0001", "1")
        assert sensor.state == "0"

    async def test_changed_value_is_never_filtered(self):
        sensor = self.make_sensor({PID_PRESENCE: "odp0001"})

        with patch("fah.devices.fah_binary_sensor.time.monotonic", return_value=1000.0):
            sensor.update_datapoint("odp0001", "0")
        assert sensor.state == "0"

        with patch("fah.devices.fah_binary_sensor.time.monotonic",
                   return_value=1000.0 + CYCLIC_PERIOD):
            sensor.update_datapoint("odp0001", "1")
        assert sensor.state == "1"

    async def test_real_event_off_the_grid_is_kept(self):
        sensor = self.make_sensor({PID_PRESENCE: "odp0001"})

        with patch("fah.devices.fah_binary_sensor.time.monotonic", return_value=1000.0):
            sensor.update_datapoint("odp0001", "1")
        sensor.state = "0"

        with patch("fah.devices.fah_binary_sensor.time.monotonic", return_value=1300.0):
            sensor.update_datapoint("odp0001", "1")
        assert sensor.state == "1"

    async def test_fire_alarm_is_never_filtered(self):
        sensor = self.make_sensor({PID_FIRE_ALARM_ACTIVE: "odp0000"})

        with patch("fah.devices.fah_binary_sensor.time.monotonic", return_value=1000.0):
            sensor.update_datapoint("odp0000", "1")
        sensor.state = "0"

        with patch("fah.devices.fah_binary_sensor.time.monotonic",
                   return_value=1000.0 + CYCLIC_PERIOD):
            sensor.update_datapoint("odp0000", "1")
        assert sensor.state == "1"

    async def test_datapoints_are_tracked_separately(self):
        sensor = self.make_sensor({PID_PRESENCE: "odp0001"})

        with patch("fah.devices.fah_binary_sensor.time.monotonic", return_value=1000.0):
            sensor.update_datapoint("odp0001", "1")
        sensor.state = "0"

        # Different datapoint, so this is not a repetition of the one above
        with patch("fah.devices.fah_binary_sensor.time.monotonic",
                   return_value=1000.0 + CYCLIC_PERIOD):
            sensor.update_datapoint("odp0002", "1")
        assert sensor.state == "1"

    async def test_sensors_do_not_share_state(self):
        first = self.make_sensor({PID_PRESENCE: "odp0001"})
        second = self.make_sensor({PID_PRESENCE: "odp0001"})

        with patch("fah.devices.fah_binary_sensor.time.monotonic", return_value=1000.0):
            first.update_datapoint("odp0001", "1")
        second.state = "0"

        with patch("fah.devices.fah_binary_sensor.time.monotonic",
                   return_value=1000.0 + CYCLIC_PERIOD):
            second.update_datapoint("odp0001", "1")
        assert second.state == "1"

    async def test_window_position_is_unaffected(self):
        sensor = self.make_sensor({PID_WINDOW_DOOR_POSITION: "odp0001"})

        with patch("fah.devices.fah_binary_sensor.time.monotonic", return_value=1000.0):
            sensor.update_datapoint("odp0001", "50")
        with patch("fah.devices.fah_binary_sensor.time.monotonic",
                   return_value=1000.0 + CYCLIC_PERIOD):
            sensor.update_datapoint("odp0001", "50")
        assert sensor.window_position == "50"
        assert sensor.state is None


class TestBinarySensorEvents:
    """Binary sensor datapoint updates must retain their protocol semantics."""

    def make_sensor(self, datapoints, function_id=0x1010):
        return FahBinarySensor(
                None, {}, "ABB700D12345", "ch0000", function_id,
                "Sensor/Dimmaktor 1/1-fach", datapoints)

    @pytest.mark.parametrize("function_id", (0x0001, 0x0031, 0x1010, 0x1012))
    async def test_verified_dimming_functions_are_detected(self, function_id):
        sensor = self.make_sensor(
                {PID_RELATIVE_SET_VALUE: "odp0003"}, function_id)

        assert sensor.supports_dimming_status()

    @pytest.mark.parametrize("function_id", (0x0000, 0x1018, 0x101A))
    async def test_non_rocker_relative_datapoint_has_no_four_state_sensor(
            self, function_id):
        sensor = self.make_sensor(
                {PID_RELATIVE_SET_VALUE: "odp0003"}, function_id)

        assert not sensor.supports_dimming_status()

    async def test_dimming_function_without_relative_datapoint_is_not_exposed(self):
        sensor = self.make_sensor({PID_SWITCH_ON_OFF: "odp0000"})

        assert not sensor.supports_dimming_status()

    async def collect_event(self, sensor, dp, value):
        events = []

        async def callback(device, event):
            assert device is sensor
            events.append(event)

        sensor.register_datapoint_updated_cb(callback)
        sensor.update_datapoint(dp, value)
        await sensor.after_update()
        sensor.unregister_datapoint_updated_cb(callback)
        return events

    @pytest.mark.parametrize(
            ("value", "expected_state"),
            (("0", False), ("1", True)))
    async def test_switch_press_remains_backward_compatible(
            self, value, expected_state):
        sensor = self.make_sensor({PID_SWITCH_ON_OFF: "odp0000"})

        events = await self.collect_event(sensor, "odp0000", value)

        assert sensor.state == ('1' if expected_state else '0')
        assert events == [{
                "pid": PID_SWITCH_ON_OFF,
                "raw_value": value,
                "command": "pressed",
                "state": expected_state,
                }]

    @pytest.mark.parametrize(
            ("value", "command", "direction", "expected_state"),
            (
                ("9", "dim_start", "up", "1"),
                ("8", "dim_stop", "up", "0"),
                ("1", "dim_start", "down", "1"),
                ("0", "dim_stop", "down", "0"),
            ))
    async def test_relative_dimming_capture_values(
            self, value, command, direction, expected_state):
        # Values captured from a Sensor/Dimmaktor 1/1-fach on 2026-08-27.
        sensor = self.make_sensor({PID_RELATIVE_SET_VALUE: "odp0003"})

        events = await self.collect_event(sensor, "odp0003", value)

        assert sensor.state == expected_state
        assert events == [{
                "pid": PID_RELATIVE_SET_VALUE,
                "raw_value": value,
                "command": command,
                "direction": direction,
                }]

    @pytest.mark.parametrize(
            ("start_value", "stop_value", "direction"),
            (("9", "8", "up"), ("1", "0", "down")))
    async def test_relative_dimming_events_are_delivered_in_order(
            self, start_value, stop_value, direction):
        sensor = self.make_sensor({PID_RELATIVE_SET_VALUE: "odp0003"})
        events = []

        async def callback(_, event):
            events.append(event)

        sensor.register_datapoint_updated_cb(callback)
        sensor.update_datapoint("odp0003", start_value)
        sensor.update_datapoint("odp0003", stop_value)
        await sensor.after_update()

        assert [event["command"] for event in events] == ["dim_start", "dim_stop"]
        assert [event["direction"] for event in events] == [direction, direction]

    async def test_relative_value_on_unrelated_datapoint_is_not_decoded(self):
        sensor = self.make_sensor({PID_SWITCH_ON_OFF: "odp0000"})

        events = await self.collect_event(sensor, "odp0000", "9")

        assert events[0]["command"] == "pressed"
        assert "direction" not in events[0]

    async def test_cyclic_relative_dimming_repeat_is_ignored(self):
        sensor = self.make_sensor({PID_RELATIVE_SET_VALUE: "odp0003"})
        events = []

        async def callback(_, event):
            events.append(event)

        sensor.register_datapoint_updated_cb(callback)
        with patch("fah.devices.fah_binary_sensor.time.monotonic", return_value=1000.0):
            sensor.update_datapoint("odp0003", "9")
        await sensor.after_update()

        with patch("fah.devices.fah_binary_sensor.time.monotonic",
                   return_value=1000.0 + CYCLIC_PERIOD):
            sensor.update_datapoint("odp0003", "9")
        await sensor.after_update()

        assert len(events) == 1

    @pytest.mark.parametrize(
            ("event", "expected"),
            (
                (
                    {"command": "pressed", "state": True},
                    {
                        "name": "Sensor/Dimmaktor 1/1-fach",
                        "serialnumber": "ABB700D12345",
                        "unique_id": "ABB700D12345/ch0000",
                        "command": "pressed",
                        "state": True,
                    },
                ),
                (
                    {"command": "dim_start", "direction": "up"},
                    {
                        "name": "Sensor/Dimmaktor 1/1-fach",
                        "serialnumber": "ABB700D12345",
                        "unique_id": "ABB700D12345/ch0000",
                        "command": "dim_start",
                        "direction": "up",
                    },
                ),
                (
                    {"command": "dim_stop", "direction": "down"},
                    {
                        "name": "Sensor/Dimmaktor 1/1-fach",
                        "serialnumber": "ABB700D12345",
                        "unique_id": "ABB700D12345/ch0000",
                        "command": "dim_stop",
                        "direction": "down",
                    },
                ),
            ))
    async def test_home_assistant_event_payload(self, event, expected):
        assert create_event_data(
                "Sensor/Dimmaktor 1/1-fach",
                "ABB700D12345",
                "ABB700D12345/ch0000",
                event) == expected

    @pytest.mark.parametrize(
            ("event", "expected"),
            (
                ({"command": "pressed", "state": True}, "pressed_up"),
                ({"command": "pressed", "state": False}, "pressed_down"),
                ({"command": "dim_start", "direction": "up"}, "held_up"),
                ({"command": "dim_start", "direction": "down"}, "held_down"),
                ({"command": "dim_stop", "direction": "up"}, None),
                ({"command": "dim_stop", "direction": "down"}, None),
            ))
    async def test_dimming_status_mapping(self, event, expected):
        assert dimming_status_from_event(event) == expected

    async def test_dimming_status_options_include_default(self):
        assert DIMMING_STATUS_DEFAULT == "not_pressed"
        assert DIMMING_STATUS_OPTIONS == [
                "not_pressed",
                "pressed_up",
                "pressed_down",
                "held_up",
                "held_down",
                ]

    async def test_repeated_dimming_status_returns_to_default_each_time(self):
        event = {"command": "pressed", "state": True}

        states = (
                dimming_status_sequence_from_event(event)
                + dimming_status_sequence_from_event(event)
                )

        assert states == (
                "pressed_up",
                "not_pressed",
                "pressed_up",
                "not_pressed",
                )

    @pytest.mark.parametrize(
            ("start_event", "held_status"),
            (
                ({"command": "dim_start", "direction": "up"}, "held_up"),
                ({"command": "dim_start", "direction": "down"}, "held_down"),
            ))
    async def test_held_status_remains_until_dim_stop(
            self, start_event, held_status):
        stop_event = {
                "command": "dim_stop",
                "direction": start_event["direction"],
                }

        assert dimming_status_sequence_from_event(start_event) == (
                held_status,
                )
        assert dimming_status_sequence_from_event(stop_event) == (
                "not_pressed",
                )

    async def test_unrelated_event_has_no_dimming_status_sequence(self):
        event = {"command": "unknown"}

        assert dimming_status_sequence_from_event(event) == ()

    async def test_dim_stop_without_direction_returns_to_default(self):
        event = {"command": "dim_stop"}

        assert dimming_status_sequence_from_event(event) == ("not_pressed",)
