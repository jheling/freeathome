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


def migrate_unique_ids(registry, sysap, integration):
    """Rename registry entries whose unique id gained the SysAP in front.

    Renaming keeps the entity id, and with it the history, the area and every
    automation that points at the entity. Adding the entity under the new
    unique id without this step would hand out a fresh entity id instead.

    Runs before the platforms are set up, so every entity is added under the
    id it will keep.
    """
    for entity_domain, device_type, suffix in SOURCES:
        for device in sysap.get_devices(device_type):
            old_unique_id = device.lookup_key + suffix
            new_unique_id = device.unique_id + suffix
            if old_unique_id == new_unique_id:
                continue

            entity_id = registry.async_get_entity_id(
                entity_domain, integration, old_unique_id
            )
            if entity_id is None:
                continue

            if registry.async_get_entity_id(
                entity_domain, integration, new_unique_id
            ):
                # Another SysAP was here first and keeps the entity id. This
                # device is added under a fresh one, where it used to be
                # dropped as a duplicate.
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


def migrate_sysap_id(registry, old_sysap_id, new_sysap_id, integration):
    """Rename registry entries when the SysAP id of an entry changes."""
    if not old_sysap_id or not new_sysap_id or old_sysap_id == new_sysap_id:
        return

    prefix = old_sysap_id + "/"
    for entry in list(registry.entities.values()):
        if entry.platform != integration or not entry.unique_id.startswith(prefix):
            continue

        new_unique_id = new_sysap_id + "/" + entry.unique_id[len(prefix):]
        if registry.async_get_entity_id(
            entry.domain, integration, new_unique_id
        ):
            _LOGGER.info(
                "Unique id %s is taken, %s keeps its own entity",
                new_unique_id,
                entry.unique_id,
            )
            continue

        _LOGGER.info(
            "Migrating unique id of %s from %s to %s",
            entry.entity_id,
            entry.unique_id,
            new_unique_id,
        )
        registry.async_update_entity(entry.entity_id, new_unique_id=new_unique_id)
