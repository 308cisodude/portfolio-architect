"""Deterministic dashboard contract for allocation and drift data."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

ALLOCATION_OVERVIEW_SCHEMA_VERSION = 1
_PERCENT_QUANTUM = Decimal("0.01")
_MONEY_QUANTUM = Decimal("0.01")
_STATUS_ORDER = ("underweight", "on_target", "overweight")


def _rounded(value: object, quantum: Decimal) -> float:
    """Return a stable half-up rounded float without negative zero."""
    rounded = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
    result = float(rounded)
    return 0.0 if result == 0 else result


def _position_row(
    position: Any, corridor_pp: float, *, include_actionable: bool = True
) -> dict[str, Any]:
    """Build one bounded, presentation-ready allocation row."""
    deviation_eur = float(position.deviation_eur)
    target_pct = float(position.target_pct)
    row = {
        "fund_id": position.fund_id,
        "fund_name": position.name,
        "wkn": position.wkn,
        "isin": position.isin,
        "allocation_status": position.allocation_status,
        "current_pct": _rounded(position.current_pct, _PERCENT_QUANTUM),
        "target_pct": _rounded(target_pct, _PERCENT_QUANTUM),
        "drift_pp": _rounded(position.deviation_pp, _PERCENT_QUANTUM),
        "current_value_eur": _rounded(position.current_value_eur, _MONEY_QUANTUM),
        "target_value_eur": _rounded(position.target_value_eur, _MONEY_QUANTUM),
        "deviation_eur": _rounded(deviation_eur, _MONEY_QUANTUM),
        "value_gap_eur": _rounded(max(0.0, -deviation_eur), _MONEY_QUANTUM),
        "excess_value_eur": _rounded(max(0.0, deviation_eur), _MONEY_QUANTUM),
        "corridor_lower_pct": _rounded(
            max(0.0, target_pct - corridor_pp), _PERCENT_QUANTUM
        ),
        "corridor_upper_pct": _rounded(
            min(100.0, target_pct + corridor_pp), _PERCENT_QUANTUM
        ),
    }
    if include_actionable:
        row["proposed_buy_eur"] = _rounded(
            position.proposed_buy_eur, _MONEY_QUANTUM
        )
        row["buy_enabled"] = bool(position.buy_enabled)
    return row


def _sort_key(position: Any) -> tuple[float, str, str]:
    """Return the documented stable sort key for one allocation group."""
    name = str(position.name).casefold()
    fund_id = str(position.fund_id)
    drift = float(position.deviation_pp)
    if position.allocation_status == "underweight":
        return (drift, name, fund_id)
    if position.allocation_status == "overweight":
        return (-drift, name, fund_id)
    return (abs(drift), name, fund_id)


def allocation_overview_state(data: Any) -> str:
    """Return the aggregate state without changing allocation semantics."""
    allocation = data.allocation
    return (
        "on_target"
        if allocation.underweight == 0 and allocation.overweight == 0
        else "drift_detected"
    )


def build_allocation_overview(
    data: Any, *, include_actionable: bool = True
) -> dict[str, Any]:
    """Return sorted allocation rows and summary metadata for Home Assistant."""
    corridor_pp = float(data.allocation.corridor_pp)
    groups: dict[str, list[Any]] = {status: [] for status in _STATUS_ORDER}
    for position in data.positions.values():
        groups[position.allocation_status].append(position)

    rows = {
        status: [
            _position_row(
                position, corridor_pp, include_actionable=include_actionable
            )
            for position in sorted(groups[status], key=_sort_key)
        ]
        for status in _STATUS_ORDER
    }
    return {
        "schema_version": ALLOCATION_OVERVIEW_SCHEMA_VERSION,
        "portfolio_value_eur": _rounded(
            data.allocation.portfolio_value_eur, _MONEY_QUANTUM
        ),
        "current_plan_value_eur": _rounded(
            data.allocation.current_plan_value_eur, _MONEY_QUANTUM
        ),
        "allocation_corridor_pp": _rounded(corridor_pp, _PERCENT_QUANTUM),
        "position_count": len(data.positions),
        "underweight_count": len(rows["underweight"]),
        "on_target_count": len(rows["on_target"]),
        "overweight_count": len(rows["overweight"]),
        **rows,
    }
