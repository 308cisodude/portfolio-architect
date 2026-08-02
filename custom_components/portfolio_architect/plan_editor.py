"""Read-only plan-editor context built from configured local files."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import re
from typing import Any

from .engine.io import load_yaml, read_positions
from .engine.importers import CsvSourceConfig
from .engine.models import Position

_ID_TOKEN_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class PlanCandidate:
    """One instrument available to the native plan editor."""

    id: str
    wkn: str
    isin: str
    name: str
    instrument_type: str
    target_pct: Decimal
    buy_enabled: bool
    selected: bool

    @property
    def label(self) -> str:
        return f"{self.name} · {self.wkn}"

    def to_option(self) -> dict[str, str]:
        return {"value": self.wkn, "label": self.label}


@dataclass(frozen=True, slots=True)
class PlanEditorContext:
    """Current plan defaults and bounded selectable candidates."""

    plan_name: str
    budget_amount: float
    candidates: tuple[PlanCandidate, ...]


def load_plan_editor_context(
    csv_path: Path,
    config_directory: Path,
    configured_instruments: list[dict[str, Any]] | None = None,
    source_config: dict[str, Any] | CsvSourceConfig | None = None,
) -> PlanEditorContext:
    """Build plan-editor choices from YAML targets and one CSV adapter."""
    adapter = (
        source_config
        if isinstance(source_config, CsvSourceConfig)
        else CsvSourceConfig.from_mapping(source_config)
    )
    positions = read_positions(csv_path, adapter)
    return load_plan_editor_context_from_positions(
        positions, config_directory, configured_instruments
    )


def load_plan_editor_context_from_positions(
    positions: dict[str, Position],
    config_directory: Path,
    configured_instruments: list[dict[str, Any]] | None = None,
) -> PlanEditorContext:
    """Build plan-editor choices from canonical positions and YAML targets."""
    portfolio_document = load_yaml(config_directory / "portfolio.yaml")
    portfolio = portfolio_document["portfolio"]

    configured_by_wkn: dict[str, dict[str, Any]] = {}
    if configured_instruments is not None:
        for item in configured_instruments:
            if isinstance(item, dict) and item.get("wkn"):
                configured_by_wkn[str(item["wkn"]).strip().upper()] = dict(item)

    yaml_by_wkn = {
        str(item["wkn"]).strip().upper(): dict(item)
        for item in portfolio.get("allocation", [])
        if isinstance(item, dict) and item.get("wkn")
    }
    all_wkns = sorted(set(positions) | set(yaml_by_wkn) | set(configured_by_wkn))
    if len(all_wkns) > 512:
        raise ValueError("too many plan-editor candidates")

    candidates: list[PlanCandidate] = []
    used_ids: set[str] = set()
    for wkn in all_wkns:
        configured = configured_by_wkn.get(wkn)
        yaml_item = yaml_by_wkn.get(wkn)
        position = positions.get(wkn)
        source = configured or yaml_item or {}
        isin = str(source.get("isin") or (position.isin if position else "")).strip().upper()
        # Plan instruments require an ISIN for policy and broker lookups. Holdings
        # without an ISIN remain visible in the whole portfolio but are not offered
        # as plan-editor candidates.
        if not isin:
            continue
        name = str(source.get("name") or (position.name if position else wkn)).strip()
        raw_id = str(source.get("id") or _derived_id(wkn)).strip()
        fund_id = _unique_id(raw_id, used_ids)
        used_ids.add(fund_id)
        target = Decimal(str(source.get("target_pct", 0)))
        selected = configured is not None or (configured_instruments is None and target > 0)
        candidates.append(
            PlanCandidate(
                id=fund_id,
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
        raise ValueError("no instruments with valid identifiers are available")
    return PlanEditorContext(
        plan_name=str(portfolio.get("name", "Investment plan")),
        budget_amount=float(portfolio.get("monthly_contribution", 0)),
        candidates=tuple(candidates),
    )


def _derived_id(wkn: str) -> str:
    token = _ID_TOKEN_RE.sub("_", wkn.casefold()).strip("_")
    return f"instrument_{token}"


def _unique_id(candidate: str, used: set[str]) -> str:
    token = _ID_TOKEN_RE.sub("_", candidate.casefold()).strip("_")[:56]
    if not token:
        token = "instrument"
    result = token
    suffix = 2
    while result in used:
        result = f"{token}_{suffix}"
        suffix += 1
    return result
