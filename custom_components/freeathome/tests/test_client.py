import pytest

from fah.pfreeathome import Client


def make_client(host):
    """Build a client without connecting to anything."""
    return Client(f"user@{host}/hass", "secret", host, 5222, "2.2.0")


def test_clients_do_not_share_their_state():
    """Every SysAP keeps its own devices, whatever their number.

    The containers used to be class attributes, so every client filled the
    same ones. With more than one SysAP each config entry then tried to add
    the entities of all of them, and Home Assistant rejected the duplicates
    with "Platform freeathome does not generate unique IDs".
    """
    clients = [make_client(f"192.0.2.{number}") for number in (1, 2, 3)]

    for number, client in enumerate(clients):
        device = f"device of SysAP {number}"
        client.devices.add(device)
        client.monitored_datapoints[f"ABB00000000{number}/ch0000/odp0000"] = device
        client.monitored_parameters[f"ABB00000000{number}/ch0000/par0000"] = device
        client.add_update_handler(lambda message: None)

    for number, client in enumerate(clients):
        assert client.devices == {f"device of SysAP {number}"}
        assert list(client.monitored_datapoints) == [f"ABB00000000{number}/ch0000/odp0000"]
        assert list(client.monitored_parameters) == [f"ABB00000000{number}/ch0000/par0000"]
        assert len(client._update_handlers) == 1
