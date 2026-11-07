import asyncio
import logging
from unittest.mock import MagicMock

import pytest
pytestmark = pytest.mark.asyncio

from fah.app_indicator import INTERVAL, indicate_forever
from fah.pfreeathome import Client


def make_client(host="192.0.2.1", **kwargs):
    """Build a client without connecting to anything."""
    return Client(f"user@{host}/hass", "secret", host, 5222, "2.2.0", **kwargs)


async def run_for(send, seconds=0.05):
    """Run the loop with a short interval, then cancel it like a disconnect does."""
    task = asyncio.ensure_future(indicate_forever(send, interval=0.005))
    await asyncio.sleep(seconds)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_interval_leaves_room_for_a_lost_call():
    """One call keeps the station sending for just under 10 minutes."""
    assert INTERVAL * 2 < 590


async def test_send_is_repeated_until_cancelled():
    calls = []

    async def send():
        calls.append(1)

    await run_for(send)

    assert len(calls) >= 2


async def test_failing_send_does_not_end_the_loop_and_warns_once(caplog):
    """The loop used to die with the first error and the value froze again."""
    calls = []

    async def send():
        calls.append(1)
        raise RuntimeError("rejected")

    with caplog.at_level(logging.WARNING):
        await run_for(send)

    assert len(calls) >= 2
    assert len([r for r in caplog.records if "failed" in r.getMessage()]) == 1


async def test_recovery_is_logged_once(caplog):
    calls = []

    async def send():
        calls.append(1)
        if len(calls) <= 3:
            raise RuntimeError("rejected")

    with caplog.at_level(logging.WARNING):
        await run_for(send)

    assert len(calls) > 4
    assert len([r for r in caplog.records if "failed" in r.getMessage()]) == 1
    assert len([r for r in caplog.records if "works again" in r.getMessage()]) == 1


async def test_second_outage_warns_again(caplog):
    calls = []

    async def send():
        calls.append(1)
        if len(calls) in (1, 2, 4, 5):
            raise RuntimeError("rejected")

    with caplog.at_level(logging.WARNING):
        await run_for(send)

    assert len(calls) > 5
    assert len([r for r in caplog.records if "failed" in r.getMessage()]) == 2
    assert len([r for r in caplog.records if "works again" in r.getMessage()]) == 2


@pytest.fixture
def client(monkeypatch):
    """A client that only records what it would send."""
    client = make_client(reconnect=False)
    client.send_presence = MagicMock()
    client.send_presence_subscription = MagicMock()
    client.send = MagicMock()
    client.get_roster = MagicMock()
    client.sent = []

    async def send_app_indicator():
        client.sent.append(1)

    client._send_app_indicator = send_app_indicator
    monkeypatch.setattr(Client, "__getitem__", lambda self, key: MagicMock())
    return client


async def test_client_starts_the_loop_on_connect_and_cancels_it_on_disconnect(client):
    await client.start(None)
    task = client._app_indicator
    assert task is not None and not task.done()
    await asyncio.sleep(0)
    assert client.sent == [1]

    await client._disconnected(None)

    assert client._app_indicator is None
    await asyncio.sleep(0)
    assert task.cancelled()


async def test_reconnect_does_not_leave_a_second_loop_behind(client):
    await client.start(None)
    first = client._app_indicator

    await client.start(None)
    await asyncio.sleep(0)

    assert first.cancelled()
    assert client._app_indicator is not first
    assert not client._app_indicator.done()

    await client._disconnected(None)


class Answer(dict):
    """Just enough of an Iq for the fault check."""

    def enable(self, name):
        pass


def answer(fault):
    return Answer(rpc_query={"method_response": {"fault": fault}})


async def test_client_sends_the_rpc_and_reports_a_fault():
    client = make_client()
    sent = []
    replies = [answer(None), answer({"string": "denied"})]

    async def send_rpc_iq(command, *argv, timeout=None, callback=None):
        sent.append(command)
        return replies.pop(0)

    client.send_rpc_iq = send_rpc_iq

    await client._send_app_indicator()
    assert sent == ["RemoteInterface.indicateConnectedApp"]

    with pytest.raises(RuntimeError, match="denied"):
        await client._send_app_indicator()
