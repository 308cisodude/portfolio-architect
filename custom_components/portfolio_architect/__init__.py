"""Portfolio Architect integration setup."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_CONFIG_DIRECTORY,
    CONF_CSV_PATH,
    CONF_PLAN_EXECUTION_DAY,
    CONF_PLAN_EXECUTION_DAYS,
    CONF_PLAN_FREQUENCY,
    CONF_PLAN_SCHEDULE_ENABLED,
    CONF_SOURCE_ENTITY_ID,
    CONF_SOURCE_PROVIDER,
    CONF_SOURCE_TYPE,
    DEFAULT_CONFIG_DIRECTORY,
    DEFAULT_SOURCE_ENTITY_ID,
    LEGACY_COMDIRECT_CSV_PROVIDER,
    DOMAIN,
    INSTANCE_UNIQUE_ID,
    PLAN_FREQUENCY_MONTHLY,
    PLATFORMS,
    SOURCE_TYPE_LEGACY_SENSOR,
    SOURCE_TYPE_LOCAL_FILES,
)
from .coordinator import PortfolioArchitectCoordinator
from .entity_ids import plan_legacy_entity_id_migrations

_LOGGER = logging.getLogger(__name__)


def _migrate_legacy_entity_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> int:
    """Rename exact duplicated-prefix IDs owned by this config entry."""
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    migrated = 0

    for migration in plan_legacy_entity_id_migrations(entries):
        existing_destination = registry.async_get(migration.new_entity_id)
        if existing_destination is not None:
            _LOGGER.error(
                "Cannot migrate %s to %s because the destination already exists",
                migration.old_entity_id,
                migration.new_entity_id,
            )
            continue

        registry.async_update_entity(
            migration.old_entity_id,
            new_entity_id=migration.new_entity_id,
        )
        migrated += 1
        _LOGGER.info(
            "Migrated Portfolio Architect entity ID from %s to %s",
            migration.old_entity_id,
            migration.new_entity_id,
        )

    return migrated


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Migrate a Portfolio Architect config entry to schema version 12."""
    _LOGGER.debug(
        "Migrating Portfolio Architect config entry from version %s.%s",
        entry.version,
        entry.minor_version,
    )

    if entry.version > 12:
        _LOGGER.error(
            "Cannot migrate Portfolio Architect config entry from future version %s",
            entry.version,
        )
        return False

    migrated_entities = 0
    if entry.version < 2:
        migrated_entities = _migrate_legacy_entity_ids(hass, entry)

    if entry.version < 3:
        # The historical local-file engine is no longer part of Portfolio Architect.
        # Preserve the old sensor reference rather than silently interpreting local
        # files with acquisition code that the current integration intentionally does
        # not contain. The operator can then reconfigure to a verified Gateway.
        old_source = entry.data.get(
            CONF_SOURCE_ENTITY_ID,
            DEFAULT_SOURCE_ENTITY_ID,
        )
        hass.config_entries.async_update_entry(
            entry,
            data={
                CONF_SOURCE_TYPE: SOURCE_TYPE_LEGACY_SENSOR,
                CONF_SOURCE_ENTITY_ID: old_source,
            },
            version=3,
        )
        _LOGGER.warning(
            "Retained the deprecated source sensor while migrating this historical "
            "entry because Portfolio Architect no longer performs local-file "
            "acquisition; reconfigure the entry to a verified REST Gateway"
        )

    if entry.version < 4:
        domain_entries = hass.config_entries.async_entries(DOMAIN)
        if len(domain_entries) == 1:
            hass.config_entries.async_update_entry(
                entry,
                unique_id=INSTANCE_UNIQUE_ID,
                version=4,
            )
            _LOGGER.info(
                "Normalized Portfolio Architect to the stable single-instance "
                "config-entry identity"
            )
        else:
            # Existing v1.1.0 installations could create duplicate entries because
            # the source path was incorrectly used as a mutable unique ID. Never
            # guess which portfolio source the user intends to retain. Keep both
            # entries loadable so they can be removed safely through the UI.
            hass.config_entries.async_update_entry(entry, version=4)
            _LOGGER.error(
                "Multiple Portfolio Architect config entries exist. Remove all "
                "duplicate entries through the Home Assistant UI and add one "
                "Portfolio Architect entry again; .storage must not be edited"
            )


    if entry.version < 5:
        options = dict(entry.options)
        legacy_execution_day = options.pop(CONF_PLAN_EXECUTION_DAY, None)
        if (
            legacy_execution_day is not None
            and not options.get(CONF_PLAN_SCHEDULE_ENABLED)
            and not isinstance(legacy_execution_day, bool)
        ):
            try:
                execution_day = int(legacy_execution_day)
            except (TypeError, ValueError):
                execution_day = 0
            if 1 <= execution_day <= 28:
                options.update({
                    CONF_PLAN_SCHEDULE_ENABLED: True,
                    CONF_PLAN_FREQUENCY: PLAN_FREQUENCY_MONTHLY,
                    CONF_PLAN_EXECUTION_DAYS: [execution_day],
                })
                _LOGGER.info(
                    "Migrated the monthly execution day to the recurring plan schedule"
                )
        hass.config_entries.async_update_entry(
            entry,
            options=options,
            version=5,
        )


    if entry.version < 6:
        data = dict(entry.data)
        if data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_LOCAL_FILES:
            data.setdefault(CONF_SOURCE_PROVIDER, LEGACY_COMDIRECT_CSV_PROVIDER)
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            version=6,
        )
        _LOGGER.info(
            "Migrated Portfolio Architect to the explicit CSV provider adapter model"
        )

    if entry.version < 7:
        # v1.4 adds the optional REST adapter. Existing CSV entries require no
        # data transformation; only advance the schema marker.
        hass.config_entries.async_update_entry(entry, version=7)
        _LOGGER.info(
            "Migrated Portfolio Architect to the local REST source-adapter schema"
        )

    if entry.version < 8:
        # v1.12 adds optional supplemental source lists in options. Existing
        # single-source entries require no transformation.
        hass.config_entries.async_update_entry(entry, version=8)
        _LOGGER.info("Migrated Portfolio Architect to the multi-source schema")

    if entry.version < 9:
        # v1.27 adds optional private-CA trust to REST source storage. Existing
        # HTTP entries intentionally remain loadable only as a temporary migration
        # state until the corresponding Gateway publishes verified TLS discovery.
        hass.config_entries.async_update_entry(entry, version=9)
        _LOGGER.info("Migrated Portfolio Architect to the verified-HTTPS transport schema")

    if entry.version < 10:
        # v1.46 retires the completed PA-side DKB CSV acquisition/migration bridge.
        # Never silently discard a still-active legacy source: installations must
        # complete the v1.45.1 verified DKB Gateway cut-over first.
        legacy_primary = entry.data.get(CONF_SOURCE_PROVIDER) == "dkb_csv"
        legacy_option_key = "supplemental_dkb_csv_paths"
        raw_legacy_paths = entry.options.get(legacy_option_key)
        legacy_supplemental = raw_legacy_paths not in (None, "", [])
        if legacy_primary or legacy_supplemental:
            _LOGGER.error(
                "Cannot migrate Portfolio Architect to schema 10 while legacy "
                "DKB CSV acquisition is still configured. Install v1.45.1, "
                "migrate the DKB CSV source to Portfolio Architect Gateway — DKB, "
                "verify provider_id dkb, then update to v1.51.0."
            )
            return False

        options = dict(entry.options)
        options.pop(legacy_option_key, None)
        hass.config_entries.async_update_entry(
            entry,
            options=options,
            version=10,
        )
        _LOGGER.info(
            "Retired the completed legacy DKB CSV migration bridge from the "
            "Portfolio Architect config entry"
        )

    if entry.version < 11:
        # v1.49 retires the one-release PA-side Comdirect CSV migration oracle.
        # Never reinterpret or discard a still-active legacy Comdirect CSV source.
        # It must be migrated through the verified v1.48.2 Gateway cut-over first.
        if (
            entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_LOCAL_FILES
            and entry.data.get(CONF_SOURCE_PROVIDER) == LEGACY_COMDIRECT_CSV_PROVIDER
        ):
            _LOGGER.error(
                "Cannot migrate Portfolio Architect to schema 11 while legacy "
                "Comdirect CSV acquisition is still configured. Install v1.48.2, "
                "migrate the source to Portfolio Architect Gateway — Comdirect in "
                "explicit csv mode, verify the Gateway-backed source, then update "
                "to v1.50.0."
            )
            return False

        hass.config_entries.async_update_entry(entry, version=11)
        _LOGGER.info(
            "Retired the completed legacy Comdirect CSV migration bridge from the "
            "Portfolio Architect config entry"
        )

    if entry.version < 12:
        # v1.51 retires the remaining provider-neutral mapped CSV acquisition path
        # from the Home Assistant integration. Never discard or reinterpret an
        # active local-file source: move it explicitly to the Generic Import Gateway
        # while still running v1.50.0, verify the Gateway-backed snapshot, and only
        # then upgrade.
        if entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_LOCAL_FILES:
            provider = entry.data.get(CONF_SOURCE_PROVIDER, "generic_csv")
            _LOGGER.error(
                "Cannot migrate Portfolio Architect to schema 12 while local CSV "
                "acquisition is still configured (provider %s). Stay on v1.50.0, "
                "install Portfolio Architect Gateway — Generic Import v1.56.0, "
                "import and verify the mapped CSV there, reconfigure Portfolio "
                "Architect to that verified REST Gateway, then retry the v1.51.0 "
                "upgrade.",
                provider,
            )
            return False

        hass.config_entries.async_update_entry(entry, version=12)
        _LOGGER.info(
            "Retired provider-neutral local CSV acquisition from the Portfolio "
            "Architect config entry; acquisition is Gateway-only in schema 12"
        )

    if migrated_entities:
        _LOGGER.info(
            "Portfolio Architect entity-ID migration renamed %s entities",
            migrated_entities,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Portfolio Architect from a config entry."""
    coordinator = PortfolioArchitectCoordinator(hass, entry)
    # Restore the bounded decision trace before any source refresh. It contains
    # only the two most recent provider-neutral evaluations.
    await coordinator.async_restore_decision_trace()
    # Restore one private, validated REST calculation before contacting the
    # Gateway so reloads and Home Assistant restarts remain serviceable during
    # a complete Gateway outage. The live refresh below replaces it only after
    # the source and current configuration validate successfully.
    await coordinator.async_restore_last_known_good()
    await coordinator.async_refresh()
    entry.runtime_data = coordinator

    if coordinator.source_type == SOURCE_TYPE_LEGACY_SENSOR:

        @callback
        def _source_state_changed(_event: Event) -> None:
            """Refresh mirrored entities after the deprecated source changes."""
            entry.async_create_background_task(
                hass,
                coordinator.async_request_refresh(),
                "Refresh Portfolio Architect entities",
                eager_start=True,
            )

        if coordinator.source_entity_id is not None:
            entry.async_on_unload(
                async_track_state_change_event(
                    hass,
                    [coordinator.source_entity_id],
                    _source_state_changed,
                )
            )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    migrated = _migrate_legacy_entity_ids(hass, entry)
    if migrated:
        _LOGGER.info(
            "Post-setup Portfolio Architect entity-ID repair renamed %s entities",
            migrated,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Portfolio Architect config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
