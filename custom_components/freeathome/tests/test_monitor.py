import pytest
pytestmark = pytest.mark.asyncio

from fah.pfreeathome import Client
from monitor import start_monitor

UPDATE = "<update><devices></devices></update>"


def make_client(host):
    """Build a client without connecting to anything."""
    return Client(f"user@{host}/hass", "secret", host, 5222, "2.2.0")


def start_all(tmp_path, hosts):
    """Start the monitor for every SysAP, in a loop like the service does."""
    clients, paths, files, finish = [], [], [], []
    for host in hosts:
        client = make_client(host)
        path = tmp_path / f"{host}.xml"
        f = open(path, "wt")
        start_monitor(client, host, f, path.name, 5, lambda _, action: finish.append(action))
        clients.append(client)
        paths.append(path)
        files.append(f)
    return clients, paths, files, finish


async def test_every_sysap_writes_its_own_file(tmp_path):
    clients, paths, _, finish = start_all(tmp_path, ["192.0.2.1", "192.0.2.2"])

    await clients[0].update_devices("<update><devices></devices><!-- one --></update>")
    await clients[1].update_devices("<update><devices></devices><!-- two --></update>")

    assert "one" in paths[0].read_text() and "two" not in paths[0].read_text()
    assert "two" in paths[1].read_text() and "one" not in paths[1].read_text()

    for action in finish:
        await action(None)


async def test_finish_removes_the_handler_of_every_sysap(tmp_path):
    clients, _, files, finish = start_all(tmp_path, ["192.0.2.1", "192.0.2.2", "192.0.2.3"])

    for action in finish:
        await action(None)

    for client, f in zip(clients, files):
        assert client._update_handlers == []
        assert f.closed
        await client.update_devices(UPDATE)


async def test_closed_file_does_not_stop_the_updates(tmp_path):
    """A stale handler must not raise, update_devices would stop right there."""
    clients, _, files, _ = start_all(tmp_path, ["192.0.2.1"])
    files[0].close()

    await clients[0].update_devices(UPDATE)

    assert clients[0]._update_handlers == []
