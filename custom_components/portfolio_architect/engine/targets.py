"""Canonical current-plan target identity for Portfolio Architect plans."""

from __future__ import annotations

import re
import secrets
from collections.abc import Collection
from typing import Any

# Legacy schema-1 and pre-v1.34 UI overrides used human-readable slugs. They remain
# accepted for backwards compatibility, but new schema-2 identities are opaque.
TARGET_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")
OPAQUE_TARGET_ID_RE = re.compile(r"^target_[0-9a-f]{32}$")
TARGET_ID_RANDOM_BYTES = 16
MAX_TARGETS = 32
SUPPORTED_PORTFOLIO_SCHEMA_VERSIONS = frozenset({1, 2})


def generate_target_id(existing: Collection[str] = ()) -> str:
    """Return a fresh opaque 128-bit current-target identity.

    The identity is generated independently from ISIN, WKN, display name and list
    position. ``existing`` is checked defensively even though a collision is already
    cryptographically negligible at Portfolio Architect's bounded target count.
    """
    used = set(existing)
    while True:
        target_id = f"target_{secrets.token_hex(TARGET_ID_RANDOM_BYTES)}"
        if target_id not in used:
            return target_id


def portfolio_schema_version(document: dict[str, Any]) -> int:
    """Return the validated portfolio-definition schema version."""
    raw = document.get("schema_version", 1)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("portfolio schema_version must be an integer")
    if raw not in SUPPORTED_PORTFOLIO_SCHEMA_VERSIONS:
        raise ValueError("portfolio schema_version is unsupported")
    return raw


def resolve_target_id(
    item: dict[str, Any],
    *,
    index: int,
    schema_version: int | None = None,
) -> str:
    """Return one stable target ID while preserving the legacy ``id`` alias.

    Portfolio schema 1 and historical UI overrides may use human-readable ``id``
    tokens. Schema 2 requires an explicit PA-style opaque 128-bit ``target_id``.
    When both keys are present they must match exactly so identity cannot drift
    silently during a migration.
    """
    explicit = item.get("target_id")
    legacy = item.get("id")

    if explicit is not None:
        if not isinstance(explicit, str) or TARGET_ID_RE.fullmatch(explicit) is None:
            raise ValueError(
                f"portfolio.allocation[{index}].target_id must match {TARGET_ID_RE.pattern}"
            )
    if legacy is not None:
        if not isinstance(legacy, str) or TARGET_ID_RE.fullmatch(legacy) is None:
            raise ValueError(
                f"portfolio.allocation[{index}].id must match {TARGET_ID_RE.pattern}"
            )
    if explicit is not None and legacy is not None and explicit != legacy:
        raise ValueError(
            f"portfolio.allocation[{index}] target_id and legacy id must match"
        )
    if (
        schema_version == 2
        and explicit is not None
        and OPAQUE_TARGET_ID_RE.fullmatch(explicit) is None
    ):
        raise ValueError(
            f"portfolio.allocation[{index}].target_id must be an opaque 128-bit PA target ID"
        )

    if schema_version == 2 and explicit is None:
        raise ValueError(
            f"portfolio.allocation[{index}].target_id is required by schema_version 2"
        )

    target_id = explicit if explicit is not None else legacy
    if target_id is None:
        key = "target_id" if schema_version == 2 else "id"
        raise ValueError(f"portfolio.allocation[{index}].{key} is required")
    return target_id


def canonicalize_target(
    item: dict[str, Any],
    *,
    index: int,
    schema_version: int | None = None,
) -> dict[str, Any]:
    """Return a target with canonical and compatibility identity keys."""
    clone = dict(item)
    target_id = resolve_target_id(
        clone,
        index=index,
        schema_version=schema_version,
    )
    clone["target_id"] = target_id
    clone["id"] = target_id
    return clone
