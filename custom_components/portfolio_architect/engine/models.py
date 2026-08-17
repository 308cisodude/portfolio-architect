from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class Position:
    """One normalized security position.

    ISIN is the canonical identity when available. ``wkn`` is secondary German
    identity metadata and may be empty for providers that do not supply a WKN.
    """

    wkn: str
    isin: str
    name: str
    instrument_type: str
    source_type: str
    value_eur: Decimal
    quantity: Decimal | None = None
    source_ids: tuple[str, ...] = ()
    source_values_eur: tuple[tuple[str, Decimal], ...] = ()


@dataclass(frozen=True, slots=True)
class Holding:
    """One imported holding in the whole-portfolio scope."""

    position_id: str
    wkn: str
    isin: str
    name: str
    instrument_type: str
    source_type: str
    current_value_eur: Decimal
    quantity: Decimal | None
    whole_portfolio_pct: Decimal
    strategy_scope: str
    plan_fund_id: str | None = None
    plan_current_pct: Decimal | None = None
    source_ids: tuple[str, ...] = ()
    source_values_eur: tuple[tuple[str, Decimal], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["source_ids"] = list(self.source_ids)
        result["source_values_eur"] = {key: value for key, value in self.source_values_eur}
        return result


@dataclass(frozen=True, slots=True)
class Recommendation:
    """One target-position recommendation inside the current plan scope."""

    fund_id: str
    wkn: str
    isin: str
    name: str
    target_pct: Decimal
    current_value_eur: Decimal
    target_value_eur: Decimal
    deviation_eur: Decimal
    current_pct: Decimal
    deviation_pp: Decimal
    allocation_status: str
    buy_enabled: bool
    proposed_buy_eur: Decimal
    execution_route: str = "legacy"
    execution_provider: str | None = None
    execution_provider_name: str | None = None
    execution_fee_data_as_of: str | None = None
    estimated_fee_eur: Decimal = Decimal("0")
    estimated_cash_outlay_eur: Decimal = Decimal("0")
    estimated_cost_ratio_pct: Decimal = Decimal("0")
    recommendation_reason: str = "legacy_allocation"
    additional_reserve_required_eur: Decimal = Decimal("0")
    deferred: bool = False
    whole_portfolio_pct: Decimal = Decimal("0")
    source_ids: tuple[str, ...] = ()
    source_values_eur: tuple[tuple[str, Decimal], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return the stable public recommendation payload contract."""
        return {
            "fund_id": self.fund_id,
            "wkn": self.wkn,
            "isin": self.isin,
            "name": self.name,
            "target_pct": self.target_pct,
            "current_value_eur": self.current_value_eur,
            "target_value_eur": self.target_value_eur,
            "deviation_eur": self.deviation_eur,
            # current_pct is deliberately the allocation inside the current plan.
            "current_pct": self.current_pct,
            "plan_current_pct": self.current_pct,
            "whole_portfolio_pct": self.whole_portfolio_pct,
            "deviation_pp": self.deviation_pp,
            "allocation_status": self.allocation_status,
            "strategy_scope": "current_plan",
            "buy_enabled": self.buy_enabled,
            "proposed_buy_eur": self.proposed_buy_eur,
            "execution_route": self.execution_route,
            "execution_provider": self.execution_provider,
            "execution_provider_name": self.execution_provider_name,
            "execution_fee_data_as_of": self.execution_fee_data_as_of,
            "estimated_fee_eur": self.estimated_fee_eur,
            "estimated_cash_outlay_eur": self.estimated_cash_outlay_eur,
            "estimated_cost_ratio_pct": self.estimated_cost_ratio_pct,
            "recommendation_reason": self.recommendation_reason,
            "additional_reserve_required_eur": self.additional_reserve_required_eur,
            "deferred": self.deferred,
            "source_count": len(self.source_ids),
            "source_ids": list(self.source_ids),
            "source_values_eur": {key: value for key, value in self.source_values_eur},
        }


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    severity: str
    status: str
    instrument_id: str | None
    message: str
    observed: Any = None
    expected: Any = None
    exception_id: str | None = None
    exception_rationale: str | None = None
    exception_approved_on: str | None = None
    exception_last_reviewed_on: str | None = None
    exception_review_on: str | None = None
    exception_review_reason: str | None = None
    exception_expected_provider: str | None = None
    exception_observed_provider: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
