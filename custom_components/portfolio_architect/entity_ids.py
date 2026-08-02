"""Stable entity-ID helpers for Portfolio Architect."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from .const import DOMAIN

LEGACY_PREFIX = f"sensor.{DOMAIN}_{DOMAIN}_"
DESIRED_PREFIX = f"sensor.{DOMAIN}_"
ALLOCATION_SUFFIXES = ("_current_allocation", "_target_allocation")


class RegistryEntryLike(Protocol):
    """Minimum registry entry surface used by the migration planner."""

    entity_id: str
    unique_id: str


@dataclass(frozen=True, slots=True)
class EntityIdMigration:
    """One safe entity-ID migration operation."""

    old_entity_id: str
    new_entity_id: str
    unique_id: str


def desired_entity_id(fund_id: str, kind: str) -> str:
    """Return the supported allocation entity ID."""
    return f"{DESIRED_PREFIX}{fund_id}_{kind}_allocation"


def legacy_entity_id(fund_id: str, kind: str) -> str:
    """Return the duplicated-prefix entity ID created by v0.4.0."""
    return f"{LEGACY_PREFIX}{fund_id}_{kind}_allocation"


def desired_entity_id_from_legacy(entity_id: str) -> str | None:
    """Return a clean ID only for the exact v0.4.0 legacy shape.

    Matching by the persisted entity ID is deliberate. The v0.4.1 and v0.4.2
    migrations depended on reconstructed unique-ID metadata, which can vary
    between already registered installations. The entity ID itself is the
    stable artefact we need to repair.
    """
    if not entity_id.startswith(LEGACY_PREFIX):
        return None

    remainder = entity_id.removeprefix(LEGACY_PREFIX)
    if not any(remainder.endswith(suffix) for suffix in ALLOCATION_SUFFIXES):
        return None

    fund_and_kind = remainder.rsplit("_", 2)
    if len(fund_and_kind) != 3 or not fund_and_kind[0]:
        return None

    return f"{DESIRED_PREFIX}{remainder}"


def plan_legacy_entity_id_migrations(
    entries: Iterable[RegistryEntryLike],
) -> list[EntityIdMigration]:
    """Plan migrations for exact v0.4.0-v0.4.2 duplicated IDs only.

    Callers must pass entries belonging to the Portfolio Architect config
    entry. User-renamed IDs and unrelated entities are intentionally ignored.
    """
    migrations: list[EntityIdMigration] = []

    for entry in entries:
        if (new_entity_id := desired_entity_id_from_legacy(entry.entity_id)) is None:
            continue
        migrations.append(
            EntityIdMigration(
                old_entity_id=entry.entity_id,
                new_entity_id=new_entity_id,
                unique_id=entry.unique_id,
            )
        )

    return migrations
