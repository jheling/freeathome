import pytest
pytestmark = pytest.mark.asyncio

import os
import logging
from async_mock import patch, AsyncMock

from fah.pfreeathome import Client
from migration import migrate_unique_ids
from common import load_fixture, init_client_state

LOG = logging.getLogger(__name__)

INTEGRATION = "freeathome"
SYSAP = "ABB700D00001"


def get_client(sysap_id=SYSAP):
    client = Client()
    client.set_datapoint = AsyncMock()
    client._host = "localhost"
    client.component_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    client.sysap_id = sysap_id

    return client


class FakeRegistry:
    """The two calls of the entity registry that the migration uses.

    Rejects a unique id that is already taken, just like the real registry.
    """

    def __init__(self, entries=None):
        # {(entity domain, integration, unique id): entity id}
        self.entries = dict(entries or {})
        self.updates = []

    def async_get_entity_id(self, entity_domain, integration, unique_id):
        return self.entries.get((entity_domain, integration, unique_id))

    def async_update_entity(self, entity_id, new_unique_id):
        key = next(k for k, v in self.entries.items() if v == entity_id)
        if (key[0], key[1], new_unique_id) in self.entries:
            raise ValueError("unique id %s already registered" % new_unique_id)
        del self.entries[key]
        self.entries[(key[0], key[1], new_unique_id)] = entity_id
        self.updates.append((entity_id, new_unique_id))


@pytest.fixture(autouse=True)
def mock_init():
    with patch("fah.pfreeathome.Client.__init__", init_client_state):
        yield

@pytest.fixture(autouse=True)
def mock_roomnames():
    with patch("fah.pfreeathome.get_room_names", return_value={"00":{"00":"room1", "01":"room2"}}):
        yield


@patch("fah.pfreeathome.Client.get_config", return_value=load_fixture("scene.xml"))
class TestVirtualDeviceUniqueId:
    async def test_virtual_device_gets_the_sysap_in_front(self, _):
        client = get_client()
        await client.find_devices(True)

        scene = next(el for el in client.get_devices("scene")
                     if el.lookup_key == "FFFF4800000F/ch0000")

        assert scene.unique_id == SYSAP + "/FFFF4800000F/ch0000"
        # The lookup key stays what the SysAP itself uses.
        assert scene.lookup_key == "FFFF4800000F/ch0000"

    async def test_virtual_device_without_a_sysap_keeps_the_plain_key(self, _):
        client = get_client(sysap_id="")
        await client.find_devices(True)

        scene = next(el for el in client.get_devices("scene")
                     if el.lookup_key == "FFFF4800000F/ch0000")

        assert scene.unique_id == "FFFF4800000F/ch0000"

    async def test_migration_renames_the_registry_entry(self, _):
        client = get_client()
        await client.find_devices(True)
        registry = FakeRegistry({
            ("scene", INTEGRATION, "FFFF4800000F/ch0000"): "scene.eigene_szene",
        })

        migrate_unique_ids(registry, client, INTEGRATION)

        assert registry.updates == [
            ("scene.eigene_szene", SYSAP + "/FFFF4800000F/ch0000"),
        ]
        # The entity id is what automations point at, it has to survive.
        assert registry.async_get_entity_id(
            "scene", INTEGRATION, SYSAP + "/FFFF4800000F/ch0000"
        ) == "scene.eigene_szene"

    async def test_migration_leaves_a_taken_unique_id_alone(self, _):
        client = get_client()
        await client.find_devices(True)
        registry = FakeRegistry({
            ("scene", INTEGRATION, "FFFF4800000F/ch0000"): "scene.eigene_szene",
            ("scene", INTEGRATION, SYSAP + "/FFFF4800000F/ch0000"): "scene.andere_szene",
        })

        migrate_unique_ids(registry, client, INTEGRATION)

        assert registry.updates == []

    async def test_migration_skips_an_unknown_entity(self, _):
        client = get_client()
        await client.find_devices(True)
        registry = FakeRegistry()

        migrate_unique_ids(registry, client, INTEGRATION)

        assert registry.updates == []


@patch("fah.pfreeathome.Client.get_config",
       return_value=load_fixture("100C_sensor_actuator_1gang.xml"))
class TestRealDeviceUniqueId:
    async def test_real_device_keeps_its_unique_id(self, _):
        client = get_client()
        await client.find_devices(True)

        light = next(iter(client.get_devices("light")))

        assert light.unique_id == light.lookup_key
        assert light.unique_id.startswith("ABB700D12345/")

    async def test_migration_does_not_touch_real_devices(self, _):
        client = get_client()
        await client.find_devices(True)
        light = next(iter(client.get_devices("light")))
        registry = FakeRegistry({
            ("light", INTEGRATION, light.lookup_key): "light.lampe",
        })

        migrate_unique_ids(registry, client, INTEGRATION)

        assert registry.updates == []
