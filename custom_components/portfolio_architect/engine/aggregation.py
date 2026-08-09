"""Privacy-safe aggregation of canonical positions from independent sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Iterable

from .models import Position

PROVIDER_MULTI_SOURCE = "multi_source"

_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


@dataclass(frozen=True, slots=True)
class PortfolioSourceSnapshot:
    """One validated source snapshot before cross-source consolidation."""

    source_id: str
    provider: str
    label: str
    generated_at: datetime
    positions: dict[str, Position]


@dataclass(frozen=True, slots=True)
class PortfolioSourceSummary:
    """Bounded non-secret contribution metadata for one source."""

    source_id: str
    provider: str
    label: str
    generated_at: datetime
    position_count: int
    contribution_eur: Decimal

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "provider": self.provider,
            "label": self.label,
            "generated_at": self.generated_at.astimezone(timezone.utc).isoformat(),
            "position_count": self.position_count,
            "contribution_eur": format(self.contribution_eur, "f"),
        }


@dataclass(frozen=True, slots=True)
class AggregationConflict:
    """One bounded identity inconsistency that did not alter the canonical key."""

    identity: str
    field: str
    observed: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"identity": self.identity, "field": self.field, "observed": list(self.observed)}


@dataclass(frozen=True, slots=True)
class AggregationResult:
    positions: dict[str, Position]
    sources: tuple[PortfolioSourceSummary, ...]
    conflicts: tuple[AggregationConflict, ...]
    oldest_generated_at: datetime
    newest_generated_at: datetime


def aggregate_sources(sources: Iterable[PortfolioSourceSnapshot]) -> AggregationResult:
    """Aggregate by ISIN, retaining exact source contributions and conflicts."""
    ordered = tuple(sources)
    if not ordered:
        raise ValueError("At least one portfolio source is required")
    seen_source_ids: set[str] = set()
    for source in ordered:
        if _SOURCE_ID_RE.fullmatch(source.source_id) is None or source.source_id in seen_source_ids:
            raise ValueError("Portfolio source IDs must be unique and machine safe")
        if not source.positions:
            raise ValueError(f"Portfolio source {source.source_id} returned no positions")
        if source.generated_at.tzinfo is None:
            raise ValueError("Portfolio source timestamps must include a timezone")
        seen_source_ids.add(source.source_id)

    groups: dict[tuple[str, str], list[tuple[PortfolioSourceSnapshot, Position]]] = {}
    for source in ordered:
        for position in source.positions.values():
            identity = ("isin", position.isin) if position.isin else ("wkn", position.wkn)
            groups.setdefault(identity, []).append((source, position))

    result: dict[str, Position] = {}
    conflicts: list[AggregationConflict] = []
    used_wkns: set[str] = set()
    for identity, members in groups.items():
        primary_source, primary = members[0]
        wkns = tuple(dict.fromkeys(item.wkn for _, item in members))
        types = tuple(dict.fromkeys(item.instrument_type for _, item in members))
        if len(wkns) > 1:
            conflicts.append(AggregationConflict(identity=identity[1], field="wkn", observed=wkns))
        if len(types) > 1:
            conflicts.append(AggregationConflict(identity=identity[1], field="instrument_type", observed=types))
        canonical_wkn = primary.wkn
        if canonical_wkn in used_wkns:
            raise ValueError(f"Cross-source aggregation produced duplicate WKN {canonical_wkn}")
        used_wkns.add(canonical_wkn)
        contribution_by_source: dict[str, Decimal] = {}
        for source, position in members:
            contribution_by_source[source.source_id] = (
                contribution_by_source.get(source.source_id, Decimal("0"))
                + position.value_eur
            )
        contributions = tuple(contribution_by_source.items())
        source_ids = tuple(contribution_by_source)
        quantities = [position.quantity for _, position in members]
        quantity = (
            sum((item for item in quantities if item is not None), Decimal("0"))
            if all(item is not None for item in quantities)
            else None
        )
        result[canonical_wkn] = Position(
            wkn=canonical_wkn,
            isin=primary.isin,
            name=primary.name,
            instrument_type=primary.instrument_type if len(types) == 1 else "other",
            source_type=primary.source_type,
            value_eur=sum((value for _, value in contributions), Decimal("0")),
            quantity=quantity,
            source_ids=source_ids,
            source_values_eur=contributions,
        )

    summaries = tuple(
        PortfolioSourceSummary(
            source_id=source.source_id,
            provider=source.provider,
            label=source.label,
            generated_at=source.generated_at,
            position_count=len(source.positions),
            contribution_eur=sum((item.value_eur for item in source.positions.values()), Decimal("0")),
        )
        for source in ordered
    )
    timestamps = tuple(source.generated_at.astimezone(timezone.utc) for source in ordered)
    return AggregationResult(
        positions=result,
        sources=summaries,
        conflicts=tuple(conflicts),
        oldest_generated_at=min(timestamps),
        newest_generated_at=max(timestamps),
    )
