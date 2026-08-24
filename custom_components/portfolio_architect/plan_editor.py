"""Read-only plan-editor context built from configured local files."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from .engine.io import load_yaml
from .engine.models import Position
from .engine.targets import canonicalize_target, portfolio_schema_version, resolve_target_id


@dataclass(frozen=True, slots=True)
class PlanCandidate:
    """One instrument available to the native plan editor."""

    # Existing current targets carry their persisted identity. A candidate that is
    # merely observed as a holding has no target identity until the user actually
    # creates a new target role from it.
    target_id: str | None
    wkn: str
    isin: str
    name: str
    instrument_type: str
    target_pct: Decimal
    buy_enabled: bool
    selected: bool

    @property
    def id(self) -> str | None:
        """Return the legacy compatibility name for an existing target ID."""
        return self.target_id

    @property
    def label(self) -> str:
        # ISIN is the canonical instrument identity. WKN remains useful German
        # metadata/fallback, but it never keys candidate or target identity.
        suffix = f" · {self.wkn}" if self.wkn else ""
        return f"{self.name} · {self.isin}{suffix}"

    def to_option(self) -> dict[str, str]:
        return {"value": self.isin, "label": self.label}


@dataclass(frozen=True, slots=True)
class PlanEditorContext:
    """Current plan defaults and bounded selectable candidates."""

    plan_name: str
    budget_amount: float
    candidates: tuple[PlanCandidate, ...]


def _normalised_isin(value: object) -> str:
    return str(value or "").strip().upper()


def _normalised_wkn(value: object) -> str:
    return str(value or "").strip().upper()


def load_plan_editor_context_from_positions(
    positions: dict[str, Position],
    config_directory: Path,
    configured_instruments: list[dict[str, Any]] | None = None,
) -> PlanEditorContext:
    """Build plan-editor choices from canonical positions and YAML targets.

    ISIN is the candidate key. WKN is retained only as secondary metadata/fallback.
    When a Home Assistant plan override is active, an unselected YAML target is only
    candidate metadata; its old target ID is deliberately *not* resurrected. If the
    user adds that instrument again, the options flow creates a fresh target role.
    """
    portfolio_document = load_yaml(config_directory / "portfolio.yaml")
    portfolio = portfolio_document["portfolio"]

    configured_by_isin: dict[str, dict[str, Any]] = {}
    if configured_instruments is not None:
        for index, item in enumerate(configured_instruments):
            if not isinstance(item, dict):
                continue
            isin = _normalised_isin(item.get("isin"))
            if not isin:
                continue
            clone = dict(item)
            try:
                clone["target_id"] = resolve_target_id(clone, index=index)
            except ValueError:
                # Legacy/corrupt UI overrides are validated before execution. The
                # editor can still expose the instrument as a candidate, but it may
                # not preserve an invalid target identity.
                clone.pop("target_id", None)
            if isin in configured_by_isin:
                raise ValueError("duplicate configured plan candidate ISIN")
            configured_by_isin[isin] = clone

    schema_version = portfolio_schema_version(portfolio_document)
    yaml_by_isin: dict[str, dict[str, Any]] = {}
    allocation = portfolio.get("allocation", [])
    if not isinstance(allocation, list):
        raise ValueError("portfolio allocation must be a list")
    for index, item in enumerate(allocation):
        if not isinstance(item, dict):
            continue
        canonical = canonicalize_target(
            item, index=index, schema_version=schema_version
        )
        isin = _normalised_isin(canonical.get("isin"))
        if not isin:
            # Plan targets require ISIN identity. Validation in the engine will
            # fail closed too; the editor should not invent identity from WKN.
            continue
        if isin in yaml_by_isin:
            raise ValueError("duplicate portfolio target ISIN")
        yaml_by_isin[isin] = canonical

    positions_by_isin: dict[str, Position] = {}
    for position in positions.values():
        isin = _normalised_isin(position.isin)
        if not isin:
            # Holdings without ISIN stay visible in whole-portfolio scope but are
            # not eligible as plan targets in the native editor.
            continue
        if isin in positions_by_isin:
            raise ValueError("duplicate plan-editor position ISIN")
        positions_by_isin[isin] = position

    all_isins = sorted(set(positions_by_isin) | set(yaml_by_isin) | set(configured_by_isin))
    if len(all_isins) > 512:
        raise ValueError("too many plan-editor candidates")

    candidates: list[PlanCandidate] = []
    for isin in all_isins:
        configured = configured_by_isin.get(isin)
        yaml_item = yaml_by_isin.get(isin)
        position = positions_by_isin.get(isin)
        source = configured or yaml_item or {}

        # An active UI override is authoritative current intent. Therefore only a
        # target that is *currently configured in that override* retains its target
        # ID. A previously removed YAML role must not be silently resurrected merely
        # because the same ISIN is selected again later.
        if configured is not None:
            target_id = configured.get("target_id")
        elif configured_instruments is None and yaml_item is not None:
            target_id = yaml_item.get("target_id")
        else:
            target_id = None

        wkn = _normalised_wkn(
            source.get("wkn") if source.get("wkn") is not None else (position.wkn if position else "")
        )
        name = str(source.get("name") or (position.name if position else isin)).strip()
        target = Decimal(str(source.get("target_pct", 0)))
        selected = configured is not None or (configured_instruments is None and target > 0)
        candidates.append(
            PlanCandidate(
                target_id=str(target_id) if target_id else None,
                wkn=wkn,
                isin=isin,
                name=name,
                instrument_type=(position.instrument_type if position else "etf"),
                target_pct=target if selected else Decimal("0"),
                buy_enabled=bool(source.get("buy_enabled", True)),
                selected=selected,
            )
        )

    if not candidates:
        raise ValueError("no instruments with valid ISIN identifiers are available")
    return PlanEditorContext(
        plan_name=str(portfolio.get("name", "Investment plan")),
        budget_amount=float(portfolio.get("monthly_contribution", 0)),
        candidates=tuple(candidates),
    )
