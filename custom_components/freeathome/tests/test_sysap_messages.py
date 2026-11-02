import pytest
pytestmark = pytest.mark.asyncio

import xml.etree.ElementTree as ET

from fah.pfreeathome import Client
from fah.sysap_messages import new_messages

ROOM = (
    '<message i="0" topic="system.notification" nameId="05C4" '
    'time="20260927201602008" severity="high">Wohnzimmer</message>'
)
LOGIC = (
    '<message i="1" topic="logic.notification" title="Achtung! Feueralarm ausgelöst!!!" '
    'time="20260927201602019" logicId="9" severity="high">Bei bestätigtem Brand ...</message>'
)
MESSAGES = f"<messages>{ROOM}{LOGIC}</messages>"


def make_client():
    """Build a client without connecting to anything."""
    return Client("user@192.0.2.1/hass", "secret", "192.0.2.1", 5222, "2.2.0")


def collect(client):
    """Register a callback on the client and return the list it fills."""
    received = []
    client.message_callback = received.append
    return received


async def test_new_message_is_read_with_all_fields():
    room, logic = new_messages(ET.fromstring(f"<update>{MESSAGES}</update>"), set())

    assert room == {
        "topic": "system.notification",
        "name_id": "05C4",
        "title": None,
        "text": "Wohnzimmer",
        "severity": "high",
        "logic_id": None,
        "time": "2026-09-27T20:16:02+00:00",
    }
    assert logic["topic"] == "logic.notification"
    assert logic["title"] == "Achtung! Feueralarm ausgelöst!!!"
    assert logic["logic_id"] == "9"
    assert logic["name_id"] is None


async def test_every_message_is_reported_once():
    seen = set()
    root = ET.fromstring(f"<update>{MESSAGES}</update>")

    assert len(new_messages(root, seen)) == 2
    assert new_messages(root, seen) == []


async def test_messages_at_start_are_seen_but_not_reported():
    client = make_client()
    received = collect(client)

    await client.update_devices(f"<project><devices/>{MESSAGES}</project>", initializing=True)
    await client.update_devices(f"<update><devices/>{MESSAGES}</update>")

    assert received == []


async def test_new_message_after_start_is_reported():
    client = make_client()
    received = collect(client)

    await client.update_devices(f"<update><devices/>{MESSAGES}</update>")

    assert [message["text"] for message in received][0] == "Wohnzimmer"


async def test_update_without_devices_does_not_raise():
    client = make_client()
    received = collect(client)

    await client.update_devices(f"<update>{MESSAGES}</update>")

    assert len(received) == 2


async def test_failing_callback_does_not_stop_the_update():
    client = make_client()
    calls = []

    def broken(message):
        calls.append(message)
        raise RuntimeError("listener failed")

    client.message_callback = broken

    await client.update_devices(f"<update><devices/>{MESSAGES}</update>")

    assert len(calls) == 2
