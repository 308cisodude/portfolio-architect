"""Privacy-safe aggregation of canonical positions from independent sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Iterable

from .identity import normalized_isin, normalized_wkn
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
    """One bounded non-identity metadata inconsistency in an aggregated position."""

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


def _wkn_to_isin_map(
    sources: tuple[PortfolioSourceSnapshot, ...],
) -> dict[str, str]:
    """Return unambiguous WKN -> ISIN evidence for fallback-only positions."""
    mapping: dict[str, str] = {}
    for source in sources:
        for position in source.positions.values():
            isin = normalized_isin(position.isin)
            wkn = normalized_wkn(position.wkn, isin=position.isin)
            if not isin or not wkn:
                continue
            previous = mapping.get(wkn)
            if previous is not None and previous != isin:
                raise ValueError(
                    f"Ambiguous instrument identity: WKN {wkn} maps to multiple ISINs"
                )
            mapping[wkn] = isin
    return mapping


def _resolved_identity(position: Position, wkn_to_isin: dict[str, str]) -> tuple[str, str]:
    """Resolve one position to ISIN primary identity or WKN fallback."""
    isin = normalized_isin(position.isin)
    if isin:
        return ("isin", isin)
    wkn = normalized_wkn(position.wkn, isin=position.isin)
    if not wkn:
        raise ValueError("Portfolio position has neither ISIN nor WKN identity")
    mapped_isin = wkn_to_isin.get(wkn)
    return ("isin", mapped_isin) if mapped_isin is not None else ("wkn", wkn)


def aggregate_sources(sources: Iterable[PortfolioSourceSnapshot]) -> AggregationResult:
    """Aggregate by ISIN first and use WKN only as an unambiguous fallback."""
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

    # ISIN is the canonical identity. A WKN-only observation may join an ISIN
    # group only when another source proves one unique WKN -> ISIN mapping.
    wkn_to_isin = _wkn_to_isin_map(ordered)
    groups: dict[tuple[str, str], list[tuple[PortfolioSourceSnapshot, Position]]] = {}
    for source in ordered:
        for position in source.positions.values():
            identity = _resolved_identity(position, wkn_to_isin)
            groups.setdefault(identity, []).append((source, position))

    result: dict[str, Position] = {}
    conflicts: list[AggregationConflict] = []
    used_output_keys: set[str] = set()
    for identity, members in groups.items():
        primary_source, primary = members[0]
        del primary_source
        isins = tuple(
            dict.fromkeys(
                token
                for _, item in members
                if (token := normalized_isin(item.isin))
            )
        )
        if identity[0] == "isin":
            if any(isin != identity[1] for isin in isins):
                raise ValueError(
                    f"Instrument identity collision for ISIN {identity[1]}"
                )
            canonical_isin = identity[1]
        else:
            if isins:
                raise ValueError(
                    f"Instrument identity collision for WKN {identity[1]}"
                )
            canonical_isin = ""

        wkns = tuple(
            dict.fromkeys(
                token
                for _, item in members
                if (token := normalized_wkn(item.wkn, isin=item.isin))
            )
        )
        if len(wkns) > 1:
            # WKN is secondary consistency evidence. It may not contradict an
            # already-established ISIN identity.
            raise ValueError(
                f"Instrument identity collision for {identity[0].upper()} {identity[1]}: "
                "multiple WKN values"
            )
        canonical_wkn = wkns[0] if wkns else ""

        types = tuple(dict.fromkeys(item.instrument_type for _, item in members))
        if len(types) > 1:
            conflicts.append(
                AggregationConflict(
                    identity=identity[1], field="instrument_type", observed=types
                )
            )

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

        # Retain the historical WKN dictionary key when a WKN exists so existing
        # internal callers remain stable. ISIN-only positions are keyed by ISIN.
        # Identity matching never relies on this implementation key.
        output_key = canonical_wkn or canonical_isin
        if not output_key or output_key in used_output_keys:
            raise ValueError("Cross-source aggregation produced duplicate instrument identity")
        used_output_keys.add(output_key)
        result[output_key] = Position(
            wkn=canonical_wkn,
            isin=canonical_isin,
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
