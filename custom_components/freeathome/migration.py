"""Keep the entity id when the unique id of a virtual device changes."""

import logging

_LOGGER = logging.getLogger(__name__)

# The entity domain, the type get_devices expects, and the suffix the platform
# appends. Only climate and the thermostat temperature sensor differ from the
# plain mapping, so the table stays next to the loop that reads it.
SOURCES = (
    ("binary_sensor", "binary_sensor", ""),
    ("climate", "thermostat", ""),
    ("cover", "cover", ""),
    ("light", "light", ""),
    ("lock", "lock", ""),
    ("scene", "scene", ""),
    ("sensor", "sensor", ""),
    ("sensor", "thermostat", "/current_temperature"),
    ("switch", "switch", ""),
)


def migrate_unique_ids(registry, sysap, integration, config_entry_id=None):
    """Rename registry entries of virtual devices to their current unique id.

    Renaming keeps the entity id, and with it the history, the area and every
    automation that points at the entity. Adding the entity under the new
    unique id without this step would hand out a fresh entity id instead.

    Two kinds of old unique id are renamed: the plain key from the time before
    the SysAP was put in front, and a key with another SysAP id in front. The
    second kind is left behind when the unique id of the config entry changes,
    for example from the entry id or an IP address to the serial number. It
    is only looked for among the entities of this config entry, because a
    virtual device has the same key on every SysAP.

    Runs before the platforms are set up, in the same setup that read the
    SysAP id, so every entity is added under the id it will keep.
    """
    own_entries = []
    if config_entry_id:
        own_entries = [
            entry
            for entry in registry.entities.values()
            if entry.platform == integration
            and entry.config_entry_id == config_entry_id
            # Home Assistant only warns about a unique id that is not a string.
            and isinstance(entry.unique_id, str)
        ]

    for entity_domain, device_type, suffix in SOURCES:
        for device in sysap.get_devices(device_type):
            plain_unique_id = device.lookup_key + suffix
            new_unique_id = device.unique_id + suffix
            if plain_unique_id == new_unique_id:
                continue

            # (entity id, old unique id), the plain key first.
            old_entries = []
            entity_id = registry.async_get_entity_id(
                entity_domain, integration, plain_unique_id
            )
            if entity_id is not None:
                old_entries.append((entity_id, plain_unique_id))

            tail = "/" + plain_unique_id
            old_entries.extend(
                (entry.entity_id, entry.unique_id)
                for entry in own_entries
                if entry.domain == entity_domain
                and entry.unique_id.endswith(tail)
                and entry.unique_id != new_unique_id
            )

            for entity_id, old_unique_id in old_entries:
                if registry.async_get_entity_id(
                    entity_domain, integration, new_unique_id
                ):
                    # The current unique id is registered already, for example
                    # by another SysAP that was here first. That entity keeps
                    # its entity id, and the old entry is left as it is.
                    _LOGGER.info(
                        "Unique id %s is taken, %s keeps its own entity",
                        new_unique_id,
                        old_unique_id,
                    )
                    continue

                _LOGGER.info(
                    "Migrating unique id of %s from %s to %s",
                    entity_id,
                    old_unique_id,
                    new_unique_id,
                )
                registry.async_update_entity(entity_id, new_unique_id=new_unique_id)
