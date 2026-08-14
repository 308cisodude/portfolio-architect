"""ISIN-first instrument identity matching with fail-closed WKN fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .models import Position


@dataclass(frozen=True, slots=True)
class PositionIdentityIndex:
    """Bounded lookup indexes for already-normalized portfolio positions."""

    by_isin: dict[str, Position]
    by_wkn: dict[str, Position]


def normalized_isin(value: str | None) -> str:
    """Return the normalized ISIN token, or an empty string when unavailable."""
    return value.strip().upper() if isinstance(value, str) and value.strip() else ""


def normalized_wkn(value: str | None, *, isin: str | None = None) -> str:
    """Return a true fallback WKN token, excluding an ISIN reused as identifier."""
    token = value.strip().upper() if isinstance(value, str) and value.strip() else ""
    isin_token = normalized_isin(isin)
    if token and isin_token and token == isin_token:
        return ""
    return token


def position_identity(position: Position) -> tuple[str, str]:
    """Return the canonical identity for one position: ISIN first, then WKN."""
    isin = normalized_isin(position.isin)
    if isin:
        return ("isin", isin)
    wkn = normalized_wkn(position.wkn, isin=position.isin)
    if wkn:
        return ("wkn", wkn)
    raise ValueError("Portfolio position has neither ISIN nor WKN identity")


def build_position_identity_index(positions: Iterable[Position]) -> PositionIdentityIndex:
    """Build unambiguous ISIN/WKN indexes and reject identity collisions."""
    by_isin: dict[str, Position] = {}
    by_wkn: dict[str, Position] = {}
    wkn_to_isin: dict[str, str] = {}

    for position in positions:
        isin = normalized_isin(position.isin)
        wkn = normalized_wkn(position.wkn, isin=position.isin)
        if not isin and not wkn:
            raise ValueError("Portfolio position has neither ISIN nor WKN identity")

        if isin:
            existing = by_isin.get(isin)
            if existing is not None and existing is not position:
                raise ValueError(f"Duplicate portfolio ISIN identity {isin}")
            by_isin[isin] = position

        if wkn:
            existing = by_wkn.get(wkn)
            if existing is not None and existing is not position:
                existing_isin = normalized_isin(existing.isin)
                if existing_isin and isin and existing_isin != isin:
                    raise ValueError(
                        f"Ambiguous instrument identity: WKN {wkn} maps to multiple ISINs"
                    )
                raise ValueError(f"Duplicate portfolio WKN identity {wkn}")
            by_wkn[wkn] = position
            if isin:
                previous_isin = wkn_to_isin.get(wkn)
                if previous_isin is not None and previous_isin != isin:
                    raise ValueError(
                        f"Ambiguous instrument identity: WKN {wkn} maps to multiple ISINs"
                    )
                wkn_to_isin[wkn] = isin

    return PositionIdentityIndex(by_isin=by_isin, by_wkn=by_wkn)


def match_position_for_target(
    fund: dict[str, Any], index: PositionIdentityIndex
) -> Position | None:
    """Match one configured target by ISIN, using WKN only when ISIN is absent.

    If both identities are available they are consistency evidence. A contradictory
    WKN may never override an ISIN mismatch, and a contradictory ISIN may never be
    hidden by a WKN fallback.
    """
    target_isin = normalized_isin(fund.get("isin"))
    target_wkn = normalized_wkn(fund.get("wkn"), isin=target_isin)
    if not target_isin and not target_wkn:
        raise ValueError("Configured target has neither ISIN nor WKN identity")

    by_isin = index.by_isin.get(target_isin) if target_isin else None
    by_wkn = index.by_wkn.get(target_wkn) if target_wkn else None

    if by_isin is not None:
        candidate_wkn = normalized_wkn(by_isin.wkn, isin=by_isin.isin)
        if target_wkn and candidate_wkn and candidate_wkn != target_wkn:
            raise ValueError(
                f"Instrument identity collision for ISIN {target_isin}: WKN mismatch"
            )
        if by_wkn is not None and by_wkn is not by_isin:
            raise ValueError(
                f"Instrument identity collision for target WKN {target_wkn}"
            )
        return by_isin

    if by_wkn is None:
        return None

    candidate_isin = normalized_isin(by_wkn.isin)
    if target_isin and candidate_isin and candidate_isin != target_isin:
        raise ValueError(
            f"Instrument identity collision for WKN {target_wkn}: ISIN mismatch"
        )
    return by_wkn
