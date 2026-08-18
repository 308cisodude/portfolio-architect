"""Data model and validation for Portfolio Architect source payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
import re
from typing import Any

MAX_POSITIONS = 32
MAX_HOLDINGS = 512
MAX_NAME_LENGTH = 160
MAX_MONEY_EUR = 1_000_000_000.0
MAX_MONTHLY_CONTRIBUTION_EUR = 10_000_000.0
PLAN_BUDGET_BASES = frozenset({"per_period", "per_execution"})
PLAN_FREQUENCIES = frozenset({"weekly", "monthly", "quarterly", "yearly"})
PLAN_CONFIGURATION_SOURCES = frozenset({"yaml", "ui"})
MAX_SUPPORTED_PAYLOAD_SCHEMA = 8
MAX_POLICY_FINDINGS = 256
MAX_POLICY_MESSAGE_LENGTH = 240
MAX_EXCEPTION_RATIONALE_LENGTH = 1200
MAX_POLICY_NUMERIC_VALUE = 100_000_000_000_000.0
POLICY_RULES = frozenset({
    "metadata",
    "ucits_required",
    "accumulating_preferred",
    "ireland_preferred",
    "max_ter_pct",
    "minimum_fund_size_eur",
    "savings_plan_required",
    "free_savings_plan_preferred",
})
POLICY_SEVERITIES = frozenset({"error", "warning", "info"})
POLICY_STATUSES = frozenset({"pass", "fail", "accepted_exception", "review_required"})

EXECUTION_ROUTES = frozenset({
    "legacy",
    "free_savings_plan",
    "paid_savings_plan",
    "manual_order",
    "unavailable",
})
EXECUTION_STATES = frozenset({
    "ready",
    "waiting_for_reserve",
    "deferred_for_cost_efficiency",
    "no_eligible_purchase",
    "reserve_unavailable",
})
RECOMMENDATION_REASONS = frozenset({
    "legacy_allocation",
    "purchase_for_underweight",
    "purchase_for_on_target",
    "purchase_for_overweight",
    "no_purchase_for_underweight",
    "no_purchase_for_on_target",
    "no_purchase_for_overweight",
    "purchase_disabled",
    "most_underweight_cost_efficient",
    "maximum_deferral_reached",
    "transaction_cost_threshold_not_met",
    "investment_reserve_unavailable",
    "execution_route_unavailable",
})
_FUND_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")
_EXECUTION_PROVIDER_RE = re.compile(r"^[a-z0-9_]{1,32}$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")
_COVERAGE_KEYS = {
    "target_positions_total",
    "target_positions_held",
    "target_positions_missing",
    "target_position_coverage_pct",
    "target_architecture_complete",
    "missing_target_fund_ids",
    "missing_target_names",
}
_MONTHLY_PLAN_KEYS = {
    "monthly_contribution_eur",
    "recommended_total_eur",
    "unallocated_contribution_eur",
    "purchase_count",
    "monthly_plan_ready",
}
_EXECUTION_SUMMARY_KEYS = {
    "available_investment_reserve_eur",
    "remaining_investment_reserve_eur",
    "investment_reserve_source",
    "investment_reserve_as_of",
    "execution_policy",
    "max_cost_ratio_pct",
    "max_orders_per_execution",
    "max_deferral_periods",
    "deferred_purchase_count",
    "deferred_contribution_eur",
    "estimated_transaction_fees_eur",
    "estimated_cash_outlay_eur",
}
_EXECUTION_UX_KEYS = {
    "execution_state",
    "additional_investment_cash_required_eur",
}
_FUNDING_SUMMARY_KEYS = {
    "provider_investment_cash",
    "provider_investment_cash_source_count",
    "funding_transfers",
    "estimated_funding_transfer_fees_eur",
    "estimated_total_execution_costs_eur",
    "funding_transfer_count",
}
_CASH_AUTHORIZATION_KEYS = {
    "investment_account_balance_eur",
    "eligible_investment_cash_eur",
    "authorized_investment_cash_eur",
    "investment_cash_authorization_policy",
    "investment_cash_authorization_cap_eur",
}
_PLAN_CONFIGURATION_KEYS = {
    "contribution_per_execution_eur",
    "plan_budget_amount_eur",
    "plan_budget_basis",
    "plan_frequency",
    "scheduled_executions_per_period",
    "plan_configuration_source",
    "plan_name",
}
_RUNTIME_KEYS = {
    "payload_schema_version",
    "engine_version",
    "generated_at",
}
_POLICY_SUMMARY_KEYS = {
    "policy_checks_evaluated",
    "policy_error_findings",
    "policy_warning_findings",
    "policy_opportunity_findings",
    "policy_accepted_exceptions",
    "mandatory_controls_compliant",
    "next_exception_review_on",
}
_POLICY_REVIEW_KEYS = {
    "exception_review_overdue",
    "overdue_exception_reviews",
    "oldest_overdue_exception_review_on",
    "last_exception_decision_on",
}
_ALLOCATION_SUMMARY_KEYS = {
    "current_portfolio_value_eur",
    "whole_portfolio_value_eur",
    "whole_portfolio_position_count",
    "current_plan_value_eur",
    "current_plan_whole_portfolio_pct",
    "current_plan_position_count",
    "current_plan_held_position_count",
    "outside_scope_value_eur",
    "outside_scope_whole_portfolio_pct",
    "outside_scope_position_count",
    "allocation_corridor_pp",
    "underweight_positions",
    "on_target_positions",
    "overweight_positions",
    "portfolio_allocation_on_target",
}
_LEGACY_ALLOCATION_SUMMARY_KEYS = _ALLOCATION_SUMMARY_KEYS - {
    "portfolio_allocation_on_target"
}


class PortfolioArchitectDataError(ValueError):
    """Raised when the source entity does not expose a valid payload."""


@dataclass(frozen=True, slots=True)
class PositionData:
    """Validated ETF position data."""

    fund_id: str
    wkn: str
    isin: str
    name: str
    target_pct: float
    current_value_eur: float
    target_value_eur: float
    deviation_eur: float
    current_pct: float
    whole_portfolio_pct: float
    deviation_pp: float
    allocation_status: str
    buy_enabled: bool
    proposed_buy_eur: float
    execution_route: str = "legacy"
    execution_provider: str | None = None
    execution_provider_name: str | None = None
    execution_fee_data_as_of: date | None = None
    funding_provider: str | None = None
    funding_provider_name: str | None = None
    funding_transfer_required: bool = False
    funding_transfer_fee_eur: float = 0.0
    funding_transfer_business_days: int = 0
    estimated_fee_eur: float = 0.0
    estimated_cash_outlay_eur: float = 0.0
    execution_state: str = "ready"
    additional_investment_cash_required_eur: float = 0.0
    estimated_cost_ratio_pct: float = 0.0
    recommendation_reason: str = "legacy_allocation"
    additional_reserve_required_eur: float = 0.0
    deferred: bool = False
    source_ids: tuple[str, ...] = ()
    source_values_eur: tuple[tuple[str, float], ...] = ()

    @property
    def target_id(self) -> str:
        """Return the explicit user-owned target identity."""
        return self.fund_id

    @property
    def is_target_position(self) -> bool:
        """Return whether the position belongs to the target architecture."""
        return self.target_pct > 0

    @property
    def is_held(self) -> bool:
        """Return whether the target position has a positive market value."""
        return self.current_value_eur > 0

    @property
    def attributes(self) -> dict[str, Any]:
        """Return stable Home Assistant state attributes."""
        return {
            "target_id": self.target_id,
            "fund_id": self.fund_id,
            "wkn": self.wkn,
            "isin": self.isin,
            "fund_name": self.name,
            "target_pct": self.target_pct,
            "current_pct": self.current_pct,
            "plan_current_pct": self.current_pct,
            "whole_portfolio_pct": self.whole_portfolio_pct,
            "strategy_scope": "current_plan",
            "deviation_pp": self.deviation_pp,
            "current_value_eur": self.current_value_eur,
            "target_value_eur": self.target_value_eur,
            "deviation_eur": self.deviation_eur,
            "allocation_status": self.allocation_status,
            "buy_enabled": self.buy_enabled,
            "proposed_buy_eur": self.proposed_buy_eur,
            "execution_route": self.execution_route,
            "execution_provider": self.execution_provider,
            "execution_provider_name": self.execution_provider_name,
            "execution_fee_data_as_of": (
                self.execution_fee_data_as_of.isoformat()
                if self.execution_fee_data_as_of is not None
                else None
            ),
            "funding_provider": self.funding_provider,
            "funding_provider_name": self.funding_provider_name,
            "funding_transfer_required": self.funding_transfer_required,
            "funding_transfer_fee_eur": self.funding_transfer_fee_eur,
            "funding_transfer_business_days": self.funding_transfer_business_days,
            "estimated_fee_eur": self.estimated_fee_eur,
            "estimated_cash_outlay_eur": self.estimated_cash_outlay_eur,
            "estimated_cost_ratio_pct": self.estimated_cost_ratio_pct,
            "recommendation_reason": self.recommendation_reason,
            "additional_reserve_required_eur": self.additional_reserve_required_eur,
            "deferred": self.deferred,
            "source_count": len(self.source_ids),
            "source_ids": list(self.source_ids),
            "source_values_eur": dict(self.source_values_eur),
        }




@dataclass(frozen=True, slots=True)
class AllocationSummaryData:
    """Validated whole-portfolio and current-plan scope summary."""

    portfolio_value_eur: float
    current_plan_value_eur: float
    outside_scope_value_eur: float
    current_plan_whole_portfolio_pct: float
    outside_scope_whole_portfolio_pct: float
    whole_portfolio_position_count: int
    current_plan_position_count: int
    current_plan_held_position_count: int
    outside_scope_position_count: int
    corridor_pp: float
    underweight: int
    on_target: int
    overweight: int

    @property
    def allocation_on_target(self) -> bool:
        return self.underweight == 0 and self.overweight == 0


@dataclass(frozen=True, slots=True)
class HoldingData:
    """One imported whole-portfolio holding."""

    position_id: str
    wkn: str
    isin: str
    name: str
    instrument_type: str
    source_type: str
    current_value_eur: float
    quantity: float | None
    whole_portfolio_pct: float
    strategy_scope: str
    plan_fund_id: str | None
    plan_current_pct: float | None
    source_ids: tuple[str, ...] = ()
    source_values_eur: tuple[tuple[str, float], ...] = ()

    @property
    def plan_target_id(self) -> str | None:
        """Return the explicit target identity for an in-plan holding."""
        return self.plan_fund_id

    @property
    def in_current_plan(self) -> bool:
        return self.strategy_scope == "current_plan"

    @property
    def attributes(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "wkn": self.wkn,
            "isin": self.isin,
            "holding_name": self.name,
            "instrument_type": self.instrument_type,
            "source_type": self.source_type,
            "current_value_eur": self.current_value_eur,
            "quantity": self.quantity,
            "whole_portfolio_pct": self.whole_portfolio_pct,
            "strategy_scope": self.strategy_scope,
            "plan_target_id": self.plan_target_id,
            "plan_fund_id": self.plan_fund_id,
            "plan_current_pct": self.plan_current_pct,
            "source_count": len(self.source_ids),
            "source_ids": list(self.source_ids),
            "source_values_eur": dict(self.source_values_eur),
        }


@dataclass(frozen=True, slots=True)
class TargetCoverageData:
    """Validated target-architecture coverage derived from positions."""

    total: int
    held: int
    missing: int
    coverage_pct: float
    missing_fund_ids: tuple[str, ...]
    missing_names: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Return whether every positive-weight target position is held."""
        return self.missing == 0

    @property
    def summary(self) -> str:
        """Return a compact language-neutral count for native cards."""
        return f"{self.held} / {self.total}"

    @property
    def attributes(self) -> dict[str, Any]:
        """Return bounded Home Assistant state attributes."""
        return {
            "held_count": self.held,
            "total_count": self.total,
            "missing_count": self.missing,
            "coverage_summary": self.summary,
            "missing_target_ids": list(self.missing_fund_ids),
            "missing_fund_ids": list(self.missing_fund_ids),
            "missing_names": list(self.missing_names),
        }


@dataclass(frozen=True, slots=True)
class ProviderInvestmentCashData:
    """Validated provider-scoped authorized investment cash."""

    provider_id: str
    provider_name: str
    available_eur: float
    remaining_eur: float
    as_of: datetime | None = None
    account_balance_eur: float | None = None
    eligible_eur: float | None = None
    authorized_eur: float | None = None
    authorization_policy: str | None = None
    authorization_cap_eur: float | None = None


@dataclass(frozen=True, slots=True)
class FundingTransferData:
    """Validated advisory transfer needed to fund planned purchases."""

    from_provider: str
    from_provider_name: str
    to_provider: str
    to_provider_name: str
    amount_eur: float
    fee_eur: float
    settlement_business_days: int


@dataclass(frozen=True, slots=True)
class MonthlyPlanData:
    """Validated recurring investment-plan summary."""

    monthly_contribution_eur: float
    contribution_per_execution_eur: float
    budget_amount_eur: float
    budget_basis: str
    frequency: str
    executions_per_period: int
    configuration_source: str
    name: str
    recommended_total_eur: float
    unallocated_contribution_eur: float
    purchase_count: int
    ready: bool
    available_reserve_eur: float = 0.0
    remaining_reserve_eur: float = 0.0
    reserve_source: str = "contribution"
    reserve_as_of: datetime | None = None
    investment_account_balance_eur: float | None = None
    eligible_investment_cash_eur: float | None = None
    authorized_investment_cash_eur: float | None = None
    investment_cash_authorization_policy: str | None = None
    investment_cash_authorization_cap_eur: float | None = None
    execution_policy: str = "legacy_distribution"
    max_cost_ratio_pct: float = 0.0
    max_orders_per_execution: int = 32
    max_deferral_periods: int = 0
    deferred_purchase_count: int = 0
    deferred_contribution_eur: float = 0.0
    estimated_transaction_fees_eur: float = 0.0
    estimated_cash_outlay_eur: float = 0.0
    execution_state: str = "ready"
    additional_investment_cash_required_eur: float = 0.0
    provider_investment_cash: tuple[ProviderInvestmentCashData, ...] = ()
    funding_transfers: tuple[FundingTransferData, ...] = ()
    estimated_funding_transfer_fees_eur: float = 0.0
    estimated_total_execution_costs_eur: float = 0.0
    funding_transfer_count: int = 0


@dataclass(frozen=True, slots=True)
class RuntimeMetadata:
    """Validated, language-neutral runtime metadata."""

    payload_schema_version: int
    engine_version: str | None
    generated_at: datetime | None




@dataclass(frozen=True, slots=True)
class PolicyFindingData:
    """One validated policy check and its stable entity metadata."""

    rule: str
    severity: str
    status: str
    instrument_id: str | None
    fund_id: str
    fund_name: str
    message: str
    observed: Any
    expected: Any
    exception_id: str | None
    exception_rationale: str | None
    exception_approved_on: date | None
    exception_last_reviewed_on: date | None
    exception_review_on: date | None
    exception_review_reason: str | None = None
    exception_expected_provider: str | None = None
    exception_observed_provider: str | None = None

    @property
    def entity_state(self) -> str:
        """Return a language-neutral state for a native enum sensor."""
        if self.status == "accepted_exception":
            return "accepted_exception"
        if self.status == "review_required":
            return "review_required"
        if self.status == "pass":
            return "pass"
        if self.severity == "error":
            return "error"
        if self.severity == "warning":
            return "warning"
        return "opportunity"

    @property
    def non_pass(self) -> bool:
        """Return whether the finding belongs on the active policy dashboard."""
        return self.status != "pass"

    @property
    def key(self) -> str:
        """Return the stable per-instrument policy finding key."""
        return f"{self.fund_id}:{self.rule}"

    @property
    def attributes(self) -> dict[str, Any]:
        """Return bounded, language-neutral Home Assistant attributes."""
        attributes: dict[str, Any] = {
            "target_id": self.fund_id,
            "fund_id": self.fund_id,
            "fund_name": self.fund_name,
            "instrument_id": self.instrument_id,
            "rule": self.rule,
            "severity": self.severity,
            "observed": _normalise_policy_value(self.rule, self.observed),
            "expected": _normalise_policy_value(self.rule, self.expected),
        }
        if self.exception_id is not None:
            attributes["exception_id"] = self.exception_id
            # The exception ID is intentionally used as a translation token.
            attributes["exception_rationale"] = self.exception_id
        if self.exception_approved_on is not None:
            attributes["exception_approved_on"] = self.exception_approved_on.isoformat()
        if self.exception_last_reviewed_on is not None:
            attributes["exception_last_reviewed_on"] = self.exception_last_reviewed_on.isoformat()
        if self.exception_review_on is not None:
            attributes["exception_review_on"] = self.exception_review_on.isoformat()
        if self.exception_review_reason is not None:
            attributes["exception_review_reason"] = self.exception_review_reason
        if self.exception_expected_provider is not None:
            attributes["exception_expected_provider"] = self.exception_expected_provider
        if self.exception_observed_provider is not None:
            attributes["exception_observed_provider"] = self.exception_observed_provider
        return attributes

    @property
    def exception_detail_attributes(self) -> dict[str, Any]:
        """Return the bounded native detail view for an accepted exception."""
        if self.status not in {"accepted_exception", "review_required"}:
            return {}
        attributes: dict[str, Any] = {
            "fund_name": self.fund_name,
            "rule": self.rule,
            "observed": _normalise_policy_value(self.rule, self.observed),
            "expected": _normalise_policy_value(self.rule, self.expected),
        }
        decision_on = self.exception_last_reviewed_on or self.exception_approved_on
        if decision_on is not None:
            attributes["decision_on"] = decision_on.isoformat()
        if self.exception_review_on is not None:
            attributes["review_on"] = self.exception_review_on.isoformat()
        if self.exception_review_reason is not None:
            attributes["review_reason"] = self.exception_review_reason
        if self.exception_expected_provider is not None:
            attributes["expected_provider"] = self.exception_expected_provider
        if self.exception_observed_provider is not None:
            attributes["observed_provider"] = self.exception_observed_provider
        return attributes


@dataclass(frozen=True, slots=True)
class PolicySummaryData:
    """Validated policy-compliance summary derived from all findings."""

    status: str
    checks_evaluated: int
    errors: int
    warnings: int
    opportunities: int
    accepted_exceptions: int
    mandatory_controls_compliant: bool
    next_exception_review_on: date | None
    review_overdue: bool
    overdue_reviews: int
    oldest_overdue_review_on: date | None
    last_exception_decision_on: date | None
    findings: dict[str, PolicyFindingData]
    exception_reviews_required: int = 0

    @property
    def non_pass_findings(self) -> tuple[PolicyFindingData, ...]:
        """Return findings that require visibility or documented acceptance."""
        return tuple(item for item in self.findings.values() if item.non_pass)


@dataclass(frozen=True, slots=True)
class PortfolioData:
    """Complete validated source data consumed by the integration."""

    positions: dict[str, PositionData]
    holdings: dict[str, HoldingData]
    allocation: AllocationSummaryData
    coverage: TargetCoverageData
    monthly_plan: MonthlyPlanData
    runtime: RuntimeMetadata
    policy: PolicySummaryData


def _required_text(
    item: dict[str, Any],
    key: str,
    index: int,
    *,
    maximum: int,
    pattern: re.Pattern[str] | None = None,
) -> str:
    value = item.get(key)
    if not isinstance(value, str):
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} must be a string"
        )
    value = value.strip()
    if not value or len(value) > maximum or any(ord(char) < 32 for char in value):
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} is empty, too long, or contains control characters"
        )
    if pattern is not None and pattern.fullmatch(value) is None:
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} has an invalid format"
        )
    return value


def _optional_float(raw: dict[str, Any], key: str, index: int, *, default: float, minimum: float, maximum: float) -> float:
    if key not in raw:
        return default
    return _required_float(raw, key, index, minimum=minimum, maximum=maximum)


def _optional_enum(
    raw: dict[str, Any],
    key: str,
    index: int,
    *,
    default: str,
    allowed: frozenset[str],
) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str) or value not in allowed:
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} is invalid"
        )
    return value


def _optional_bool(raw: dict[str, Any], key: str, index: int, *, default: bool) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} must be boolean"
        )
    return value


def _required_float(
    item: dict[str, Any],
    key: str,
    index: int,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = item.get(key)
    if isinstance(value, bool):
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} must be numeric"
        )
    try:
        number = float(value)
    except (TypeError, ValueError) as err:
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} must be numeric"
        ) from err
    if not math.isfinite(number):
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} must be finite"
        )
    if minimum is not None and number < minimum:
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} is below the allowed range"
        )
    if maximum is not None and number > maximum:
        raise PortfolioArchitectDataError(
            f"recommendations[{index}].{key} exceeds the allowed range"
        )
    return number


def _summary_float(
    summary: dict[str, Any],
    key: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = summary.get(key)
    if isinstance(value, bool):
        raise PortfolioArchitectDataError(f"summary.{key} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as err:
        raise PortfolioArchitectDataError(f"summary.{key} must be numeric") from err
    if not math.isfinite(number):
        raise PortfolioArchitectDataError(f"summary.{key} must be finite")
    if minimum is not None and number < minimum:
        raise PortfolioArchitectDataError(f"summary.{key} is below the allowed range")
    if maximum is not None and number > maximum:
        raise PortfolioArchitectDataError(f"summary.{key} exceeds the allowed range")
    return number



def _parse_source_provenance(raw: dict[str, Any], *, context: str) -> tuple[tuple[str, ...], tuple[tuple[str, float], ...]]:
    """Validate optional bounded source provenance added by multi-source payloads."""
    raw_ids = raw.get("source_ids", [])
    raw_values = raw.get("source_values_eur", {})
    if not isinstance(raw_ids, (list, tuple)) or len(raw_ids) > 16:
        raise PortfolioArchitectDataError(f"{context}.source_ids must be a bounded list")
    ids: list[str] = []
    for value in raw_ids:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > 32
            or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in value)
            or value in ids
        ):
            raise PortfolioArchitectDataError(f"{context}.source_ids contains an invalid source ID")
        ids.append(value)
    if isinstance(raw_values, dict):
        raw_items = list(raw_values.items())
    elif isinstance(raw_values, (list, tuple)):
        raw_items = list(raw_values)
    else:
        raise PortfolioArchitectDataError(f"{context}.source_values_eur must be a bounded object")
    if len(raw_items) > 16 or any(not isinstance(item, (list, tuple)) or len(item) != 2 for item in raw_items):
        raise PortfolioArchitectDataError(f"{context}.source_values_eur must be a bounded object")
    values: list[tuple[str, float]] = []
    for source_id, amount in raw_items:
        if source_id not in ids:
            raise PortfolioArchitectDataError(f"{context}.source_values_eur contains an unknown source ID")
        try:
            number = float(amount)
        except (TypeError, ValueError) as err:
            raise PortfolioArchitectDataError(f"{context}.source_values_eur must be numeric") from err
        if not math.isfinite(number) or number < 0 or number > MAX_MONEY_EUR:
            raise PortfolioArchitectDataError(f"{context}.source_values_eur is outside the allowed range")
        values.append((source_id, number))
    if ids and set(source_id for source_id, _ in values) != set(ids):
        raise PortfolioArchitectDataError(f"{context}.source_values_eur is incomplete")
    return tuple(ids), tuple(values)

def parse_recommendations(value: Any) -> dict[str, PositionData]:
    """Validate recommendations and index them by stable fund ID."""
    if not isinstance(value, list) or not value:
        raise PortfolioArchitectDataError(
            "The source entity must expose a non-empty recommendations attribute"
        )
    if len(value) > MAX_POSITIONS:
        raise PortfolioArchitectDataError(
            f"The source entity may expose at most {MAX_POSITIONS} recommendations"
        )

    positions: dict[str, PositionData] = {}
    seen_wkns: set[str] = set()
    seen_isins: set[str] = set()

    for index, raw_item in enumerate(value):
        if not isinstance(raw_item, dict):
            raise PortfolioArchitectDataError(
                f"recommendations[{index}] must be an object"
            )

        fund_id = _required_text(
            raw_item,
            "fund_id",
            index,
            maximum=64,
            pattern=_FUND_ID_RE,
        )
        if fund_id in positions:
            raise PortfolioArchitectDataError(
                f"Duplicate fund_id in recommendations: {fund_id}"
            )
        raw_target_id = raw_item.get("target_id")
        if raw_target_id is not None:
            if (
                not isinstance(raw_target_id, str)
                or _FUND_ID_RE.fullmatch(raw_target_id) is None
                or raw_target_id != fund_id
            ):
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}].target_id is inconsistent with fund_id"
                )

        wkn = _required_text(raw_item, "wkn", index, maximum=16)
        isin = _required_text(raw_item, "isin", index, maximum=32)
        if wkn in seen_wkns:
            raise PortfolioArchitectDataError(f"Duplicate WKN in recommendations: {wkn}")
        if isin in seen_isins:
            raise PortfolioArchitectDataError(f"Duplicate ISIN in recommendations: {isin}")
        seen_wkns.add(wkn)
        seen_isins.add(isin)

        allocation_status = _required_text(
            raw_item, "allocation_status", index, maximum=16
        )
        if allocation_status not in {"underweight", "on_target", "overweight"}:
            raise PortfolioArchitectDataError(
                f"recommendations[{index}].allocation_status is invalid"
            )

        buy_enabled = raw_item.get("buy_enabled")
        if not isinstance(buy_enabled, bool):
            raise PortfolioArchitectDataError(
                f"recommendations[{index}].buy_enabled must be boolean"
            )

        source_ids, source_values_eur = _parse_source_provenance(
            raw_item, context=f"recommendations[{index}]"
        )
        execution_provider = raw_item.get("execution_provider")
        if execution_provider is not None:
            if (
                not isinstance(execution_provider, str)
                or _EXECUTION_PROVIDER_RE.fullmatch(execution_provider) is None
            ):
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}].execution_provider is invalid"
                )
        execution_provider_name = raw_item.get("execution_provider_name")
        if execution_provider_name is not None:
            if (
                not isinstance(execution_provider_name, str)
                or not execution_provider_name.strip()
                or len(execution_provider_name.strip()) > 80
                or any(ord(char) < 32 for char in execution_provider_name)
            ):
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}].execution_provider_name is invalid"
                )
            execution_provider_name = execution_provider_name.strip()
        execution_fee_data_as_of = None
        raw_fee_as_of = raw_item.get("execution_fee_data_as_of")
        if raw_fee_as_of is not None:
            if not isinstance(raw_fee_as_of, str) or len(raw_fee_as_of) > 16:
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}].execution_fee_data_as_of is invalid"
                )
            try:
                execution_fee_data_as_of = date.fromisoformat(raw_fee_as_of)
            except ValueError as err:
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}].execution_fee_data_as_of is invalid"
                ) from err
        funding_provider = raw_item.get("funding_provider")
        if funding_provider is not None and (
            not isinstance(funding_provider, str)
            or _EXECUTION_PROVIDER_RE.fullmatch(funding_provider) is None
        ):
            raise PortfolioArchitectDataError(
                f"recommendations[{index}].funding_provider is invalid"
            )
        funding_provider_name = raw_item.get("funding_provider_name")
        if funding_provider_name is not None:
            if (
                not isinstance(funding_provider_name, str)
                or not funding_provider_name.strip()
                or len(funding_provider_name.strip()) > 80
                or any(ord(char) < 32 for char in funding_provider_name)
            ):
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}].funding_provider_name is invalid"
                )
            funding_provider_name = funding_provider_name.strip()
        funding_transfer_required = _optional_bool(
            raw_item, "funding_transfer_required", index, default=False
        )
        funding_transfer_fee_eur = _optional_float(
            raw_item, "funding_transfer_fee_eur", index, default=0.0, minimum=0, maximum=MAX_MONEY_EUR
        )
        funding_transfer_business_days = raw_item.get("funding_transfer_business_days", 0)
        if (
            isinstance(funding_transfer_business_days, bool)
            or not isinstance(funding_transfer_business_days, int)
            or not 0 <= funding_transfer_business_days <= 30
        ):
            raise PortfolioArchitectDataError(
                f"recommendations[{index}].funding_transfer_business_days is invalid"
            )
        if funding_provider is None:
            if funding_provider_name is not None or funding_transfer_required or funding_transfer_fee_eur or funding_transfer_business_days:
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}] contains funding metadata without a funding provider"
                )
        else:
            if execution_provider is None:
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}] funding provider requires an execution provider"
                )
            if funding_transfer_required != (funding_provider != execution_provider):
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}] funding-transfer relationship is inconsistent"
                )
            if not funding_transfer_required and (funding_transfer_fee_eur or funding_transfer_business_days):
                raise PortfolioArchitectDataError(
                    f"recommendations[{index}] same-provider funding must not contain transfer cost or delay"
                )
        positions[fund_id] = PositionData(
            fund_id=fund_id,
            wkn=wkn,
            isin=isin,
            name=_required_text(raw_item, "name", index, maximum=MAX_NAME_LENGTH),
            target_pct=_required_float(
                raw_item, "target_pct", index, minimum=0, maximum=100
            ),
            current_value_eur=_required_float(
                raw_item,
                "current_value_eur",
                index,
                minimum=0,
                maximum=MAX_MONEY_EUR,
            ),
            target_value_eur=_required_float(
                raw_item,
                "target_value_eur",
                index,
                minimum=0,
                maximum=MAX_MONEY_EUR,
            ),
            deviation_eur=_required_float(
                raw_item,
                "deviation_eur",
                index,
                minimum=-MAX_MONEY_EUR,
                maximum=MAX_MONEY_EUR,
            ),
            current_pct=_required_float(
                raw_item, "current_pct", index, minimum=0, maximum=100
            ),
            whole_portfolio_pct=_required_float(
                raw_item,
                "whole_portfolio_pct" if "whole_portfolio_pct" in raw_item else "current_pct",
                index,
                minimum=0,
                maximum=100,
            ),
            deviation_pp=_required_float(
                raw_item, "deviation_pp", index, minimum=-100, maximum=100
            ),
            allocation_status=allocation_status,
            buy_enabled=buy_enabled,
            proposed_buy_eur=_required_float(
                raw_item,
                "proposed_buy_eur",
                index,
                minimum=0,
                maximum=MAX_MONEY_EUR,
            ),
            execution_route=_optional_enum(
                raw_item,
                "execution_route",
                index,
                default="legacy",
                allowed=EXECUTION_ROUTES,
            ),
            execution_provider=execution_provider,
            execution_provider_name=execution_provider_name,
            execution_fee_data_as_of=execution_fee_data_as_of,
            funding_provider=funding_provider,
            funding_provider_name=funding_provider_name,
            funding_transfer_required=funding_transfer_required,
            funding_transfer_fee_eur=funding_transfer_fee_eur,
            funding_transfer_business_days=funding_transfer_business_days,
            estimated_fee_eur=_optional_float(raw_item, "estimated_fee_eur", index, default=0.0, minimum=0, maximum=MAX_MONEY_EUR),
            estimated_cash_outlay_eur=_optional_float(raw_item, "estimated_cash_outlay_eur", index, default=0.0, minimum=0, maximum=MAX_MONEY_EUR),
            estimated_cost_ratio_pct=_optional_float(raw_item, "estimated_cost_ratio_pct", index, default=0.0, minimum=0, maximum=100),
            recommendation_reason=_optional_enum(
                raw_item,
                "recommendation_reason",
                index,
                default="legacy_allocation",
                allowed=RECOMMENDATION_REASONS,
            ),
            additional_reserve_required_eur=_optional_float(raw_item, "additional_reserve_required_eur", index, default=0.0, minimum=0, maximum=MAX_MONEY_EUR),
            deferred=_optional_bool(raw_item, "deferred", index, default=False),
            source_ids=source_ids,
            source_values_eur=source_values_eur,
        )

    for position in positions.values():
        if position.deferred and position.proposed_buy_eur > 0:
            raise PortfolioArchitectDataError(
                "A deferred recommendation cannot contain a proposed purchase"
            )
        if position.proposed_buy_eur > 0 and position.execution_route != "legacy":
            expected_outlay = (
                position.proposed_buy_eur
                + position.estimated_fee_eur
                + position.funding_transfer_fee_eur
            )
            if not math.isclose(
                position.estimated_cash_outlay_eur,
                expected_outlay,
                rel_tol=0,
                abs_tol=0.01,
            ):
                raise PortfolioArchitectDataError(
                    "Recommendation cash outlay is inconsistent with principal and fee"
                )

    target_sum = sum(position.target_pct for position in positions.values())
    if not math.isclose(target_sum, 100.0, rel_tol=0, abs_tol=1e-6):
        raise PortfolioArchitectDataError(
            f"Target allocation must sum to 100%, got {target_sum}%"
        )

    current_total_value = sum(
        position.current_value_eur for position in positions.values()
    )
    current_pct_sum = sum(position.current_pct for position in positions.values())
    expected_current_sum = 100.0 if current_total_value > 0 else 0.0
    if not math.isclose(
        current_pct_sum,
        expected_current_sum,
        rel_tol=0,
        abs_tol=0.01,
    ):
        raise PortfolioArchitectDataError(
            "Current allocation percentages are inconsistent with portfolio value"
        )

    return positions



def parse_holdings(value: Any, positions: dict[str, PositionData]) -> dict[str, HoldingData]:
    """Validate every imported whole-portfolio holding."""
    if not isinstance(value, list) or not value:
        raise PortfolioArchitectDataError(
            "The source entity must expose a non-empty holdings attribute"
        )
    if len(value) > MAX_HOLDINGS:
        raise PortfolioArchitectDataError(
            f"The source entity may expose at most {MAX_HOLDINGS} holdings"
        )

    holdings: dict[str, HoldingData] = {}
    seen_wkns: set[str] = set()
    seen_isins: set[str] = set()
    allowed_types = {
        "etf", "stock", "fund", "bond", "certificate", "warrant",
        "commodity", "note", "other",
    }
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise PortfolioArchitectDataError(f"holdings[{index}] must be an object")

        position_id = raw.get("position_id")
        if (
            not isinstance(position_id, str)
            or _FUND_ID_RE.fullmatch(position_id) is None
            or position_id in holdings
        ):
            raise PortfolioArchitectDataError(f"holdings[{index}].position_id is invalid or duplicate")
        wkn = raw.get("wkn")
        if not isinstance(wkn, str) or len(wkn.strip()) > 16:
            raise PortfolioArchitectDataError(f"holdings[{index}].wkn is invalid")
        wkn = wkn.strip().upper()

        isin = raw.get("isin")
        if not isinstance(isin, str) or len(isin.strip()) > 32:
            raise PortfolioArchitectDataError(f"holdings[{index}].isin is invalid")
        isin = isin.strip().upper()
        if not wkn and not isin:
            raise PortfolioArchitectDataError(
                f"holdings[{index}] must expose an ISIN or WKN identity"
            )
        if wkn:
            if wkn in seen_wkns:
                raise PortfolioArchitectDataError(f"Duplicate WKN in holdings: {wkn}")
            seen_wkns.add(wkn)
        if isin:
            if isin in seen_isins:
                raise PortfolioArchitectDataError(f"Duplicate ISIN in holdings: {isin}")
            seen_isins.add(isin)

        name = raw.get("name")
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name.strip()) > MAX_NAME_LENGTH
            or any(ord(char) < 32 for char in name)
        ):
            raise PortfolioArchitectDataError(f"holdings[{index}].name is invalid")
        instrument_type = raw.get("instrument_type")
        if instrument_type not in allowed_types:
            raise PortfolioArchitectDataError(f"holdings[{index}].instrument_type is invalid")
        source_type = raw.get("source_type")
        if (
            not isinstance(source_type, str)
            or not source_type.strip()
            or len(source_type.strip()) > 64
            or any(ord(char) < 32 for char in source_type)
        ):
            raise PortfolioArchitectDataError(f"holdings[{index}].source_type is invalid")
        scope = raw.get("strategy_scope")
        if scope not in {"current_plan", "outside_scope"}:
            raise PortfolioArchitectDataError(f"holdings[{index}].strategy_scope is invalid")
        value_eur = _required_float(raw, "current_value_eur", index, minimum=0, maximum=MAX_MONEY_EUR)
        quantity_raw = raw.get("quantity")
        if quantity_raw is None:
            quantity = None
        else:
            try:
                quantity = float(quantity_raw)
            except (TypeError, ValueError) as err:
                raise PortfolioArchitectDataError(f"holdings[{index}].quantity is invalid") from err
            if not math.isfinite(quantity) or quantity < 0 or quantity > 1_000_000_000_000:
                raise PortfolioArchitectDataError(f"holdings[{index}].quantity is invalid")
        whole_pct = _required_float(raw, "whole_portfolio_pct", index, minimum=0, maximum=100)
        plan_fund_id = raw.get("plan_fund_id")
        plan_target_id = raw.get("plan_target_id")
        if plan_target_id is not None and plan_target_id != plan_fund_id:
            raise PortfolioArchitectDataError(
                f"holdings[{index}].plan_target_id is inconsistent with plan_fund_id"
            )
        plan_current_pct_raw = raw.get("plan_current_pct")
        if scope == "current_plan":
            if (
                not isinstance(plan_fund_id, str)
                or plan_fund_id not in positions
                or positions[plan_fund_id].wkn != wkn
            ):
                raise PortfolioArchitectDataError(f"holdings[{index}] current-plan identity is inconsistent")
            try:
                plan_current_pct = float(plan_current_pct_raw)
            except (TypeError, ValueError) as err:
                raise PortfolioArchitectDataError(f"holdings[{index}].plan_current_pct is invalid") from err
            if not math.isfinite(plan_current_pct) or not 0 <= plan_current_pct <= 100:
                raise PortfolioArchitectDataError(f"holdings[{index}].plan_current_pct is invalid")
            if not math.isclose(plan_current_pct, positions[plan_fund_id].current_pct, rel_tol=0, abs_tol=1e-6):
                raise PortfolioArchitectDataError(f"holdings[{index}].plan_current_pct is inconsistent")
        else:
            if (
                plan_fund_id is not None
                or plan_target_id is not None
                or plan_current_pct_raw is not None
            ):
                raise PortfolioArchitectDataError(f"holdings[{index}] outside-scope metadata is inconsistent")
            plan_current_pct = None

        source_ids, source_values_eur = _parse_source_provenance(
            raw, context=f"holdings[{index}]"
        )
        holdings[position_id] = HoldingData(
            position_id=position_id,
            wkn=wkn,
            isin=isin,
            name=name.strip(),
            instrument_type=instrument_type,
            source_type=source_type.strip(),
            current_value_eur=value_eur,
            quantity=quantity,
            whole_portfolio_pct=whole_pct,
            strategy_scope=scope,
            plan_fund_id=plan_fund_id,
            plan_current_pct=plan_current_pct,
            source_ids=source_ids,
            source_values_eur=source_values_eur,
        )

    whole_value = sum(item.current_value_eur for item in holdings.values())
    whole_pct_sum = sum(item.whole_portfolio_pct for item in holdings.values())
    if whole_value <= 0:
        raise PortfolioArchitectDataError("Whole portfolio value must be positive")
    if not math.isclose(whole_pct_sum, 100.0, rel_tol=0, abs_tol=0.01):
        raise PortfolioArchitectDataError("Whole-portfolio percentages must sum to 100%")
    for item in holdings.values():
        expected_pct = item.current_value_eur / whole_value * 100.0
        if not math.isclose(item.whole_portfolio_pct, expected_pct, rel_tol=0, abs_tol=0.01):
            raise PortfolioArchitectDataError(f"holdings[{item.position_id}].whole_portfolio_pct is inconsistent")

    current_plan_wkns = {item.wkn for item in holdings.values() if item.in_current_plan}
    recommendation_wkns = {position.wkn for position in positions.values()}
    held_plan_wkns = {position.wkn for position in positions.values() if position.current_value_eur > 0}
    if not current_plan_wkns.issubset(recommendation_wkns) or not held_plan_wkns.issubset(current_plan_wkns):
        raise PortfolioArchitectDataError("Current-plan holdings are inconsistent with recommendations")
    return holdings

def calculate_target_coverage(
    positions: dict[str, PositionData],
) -> TargetCoverageData:
    """Derive target coverage from validated positive-weight positions."""
    target_positions = tuple(
        position for position in positions.values() if position.is_target_position
    )
    if not target_positions:
        raise PortfolioArchitectDataError(
            "At least one positive-weight target position is required"
        )

    missing_positions = tuple(
        position for position in target_positions if not position.is_held
    )
    total = len(target_positions)
    missing = len(missing_positions)
    held = total - missing

    return TargetCoverageData(
        total=total,
        held=held,
        missing=missing,
        coverage_pct=held / total * 100.0,
        missing_fund_ids=tuple(position.fund_id for position in missing_positions),
        missing_names=tuple(position.name for position in missing_positions),
    )


def _parse_allocation_summary(
    summary: dict[str, Any],
    positions: dict[str, PositionData],
    holdings: dict[str, HoldingData],
    *,
    require_complete_contract: bool,
) -> AllocationSummaryData:
    """Validate whole-portfolio totals and current-plan drift classifications."""
    if require_complete_contract and not _ALLOCATION_SUMMARY_KEYS.issubset(summary):
        missing = sorted(_ALLOCATION_SUMMARY_KEYS - set(summary))
        raise PortfolioArchitectDataError(
            f"summary is missing the allocation scope contract: {', '.join(missing)}"
        )

    whole_value = sum(item.current_value_eur for item in holdings.values())
    current_plan_value = sum(position.current_value_eur for position in positions.values())
    outside_value = whole_value - current_plan_value
    plan_whole_pct = current_plan_value / whole_value * 100.0 if whole_value else 0.0
    outside_whole_pct = outside_value / whole_value * 100.0 if whole_value else 0.0
    current_plan_holdings = [item for item in holdings.values() if item.in_current_plan]
    outside_holdings = [item for item in holdings.values() if not item.in_current_plan]

    expected_numeric = {
        "current_portfolio_value_eur": whole_value,
        "whole_portfolio_value_eur": whole_value,
        "current_plan_value_eur": current_plan_value,
        "current_plan_whole_portfolio_pct": plan_whole_pct,
        "outside_scope_value_eur": outside_value,
        "outside_scope_whole_portfolio_pct": outside_whole_pct,
    }
    for key, expected_value in expected_numeric.items():
        if key not in summary:
            if require_complete_contract:
                raise PortfolioArchitectDataError(f"summary.{key} is missing")
            continue
        maximum = 100 if key.endswith("_pct") else MAX_MONEY_EUR
        source_value = _summary_float(summary, key, minimum=0, maximum=maximum)
        tolerance = 0.01 if key.endswith("_eur") else 1e-6
        if not math.isclose(source_value, expected_value, rel_tol=0, abs_tol=tolerance):
            raise PortfolioArchitectDataError(f"summary.{key} is inconsistent")

    expected_counts = {
        "whole_portfolio_position_count": len(holdings),
        "current_plan_position_count": len(positions),
        "current_plan_held_position_count": sum(1 for item in positions.values() if item.current_value_eur > 0),
        "outside_scope_position_count": len(outside_holdings),
    }
    for key, expected_value in expected_counts.items():
        if key not in summary:
            if require_complete_contract:
                raise PortfolioArchitectDataError(f"summary.{key} is missing")
            continue
        value = summary.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value != expected_value:
            raise PortfolioArchitectDataError(f"summary.{key} is inconsistent")

    corridor = (
        _summary_float(summary, "allocation_corridor_pp", minimum=0, maximum=100)
        if "allocation_corridor_pp" in summary
        else 1.0
    )
    counts = {
        state: sum(1 for item in positions.values() if item.allocation_status == state)
        for state in ("underweight", "on_target", "overweight")
    }
    for position in positions.values():
        expected_status = (
            "underweight"
            if position.deviation_pp < -corridor - 1e-9
            else "overweight"
            if position.deviation_pp > corridor + 1e-9
            else "on_target"
        )
        if position.allocation_status != expected_status:
            raise PortfolioArchitectDataError(
                f"recommendations[{position.fund_id}].allocation_status is inconsistent with the corridor"
            )

    expected_classification = {
        "underweight_positions": counts["underweight"],
        "on_target_positions": counts["on_target"],
        "overweight_positions": counts["overweight"],
        "portfolio_allocation_on_target": counts["underweight"] == 0 and counts["overweight"] == 0,
    }
    for key, expected_value in expected_classification.items():
        if key not in summary:
            if require_complete_contract:
                raise PortfolioArchitectDataError(f"summary.{key} is missing")
            continue
        if summary.get(key) != expected_value:
            raise PortfolioArchitectDataError(f"summary.{key} is inconsistent")

    return AllocationSummaryData(
        portfolio_value_eur=whole_value,
        current_plan_value_eur=current_plan_value,
        outside_scope_value_eur=outside_value,
        current_plan_whole_portfolio_pct=plan_whole_pct,
        outside_scope_whole_portfolio_pct=outside_whole_pct,
        whole_portfolio_position_count=len(holdings),
        current_plan_position_count=len(positions),
        current_plan_held_position_count=sum(1 for item in positions.values() if item.current_value_eur > 0),
        outside_scope_position_count=len(outside_holdings),
        corridor_pp=corridor,
        underweight=counts["underweight"],
        on_target=counts["on_target"],
        overweight=counts["overweight"],
    )


def _validate_source_coverage(
    summary: dict[str, Any],
    coverage: TargetCoverageData,
) -> None:
    present = _COVERAGE_KEYS.intersection(summary)
    if not present:
        return
    if present != _COVERAGE_KEYS:
        raise PortfolioArchitectDataError(
            "summary contains an incomplete target coverage contract"
        )

    expected = {
        "target_positions_total": coverage.total,
        "target_positions_held": coverage.held,
        "target_positions_missing": coverage.missing,
        "target_architecture_complete": coverage.complete,
        "missing_target_fund_ids": list(coverage.missing_fund_ids),
        "missing_target_names": list(coverage.missing_names),
    }
    for key, expected_value in expected.items():
        if summary.get(key) != expected_value:
            raise PortfolioArchitectDataError(
                f"summary.{key} is inconsistent with recommendations"
            )

    if (
        "missing_target_ids" in summary
        and summary.get("missing_target_ids") != list(coverage.missing_fund_ids)
    ):
        raise PortfolioArchitectDataError(
            "summary.missing_target_ids is inconsistent with recommendations"
        )

    source_pct = _summary_float(
        summary, "target_position_coverage_pct", minimum=0, maximum=100
    )
    if not math.isclose(
        source_pct, coverage.coverage_pct, rel_tol=0, abs_tol=1e-6
    ):
        raise PortfolioArchitectDataError(
            "summary.target_position_coverage_pct is inconsistent with recommendations"
        )


def _parse_provider_investment_cash(raw: Any) -> tuple[ProviderInvestmentCashData, ...]:
    """Validate bounded provider-scoped investment-cash summary metadata."""

    if not isinstance(raw, list) or len(raw) > 16:
        raise PortfolioArchitectDataError("summary.provider_investment_cash must be a bounded list")
    seen: set[str] = set()
    result: list[ProviderInvestmentCashData] = []

    def number(item: dict[str, Any], key: str, *, minimum: float = 0.0) -> float | None:
        value = item.get(key)
        if value is None:
            return None
        if isinstance(value, bool):
            raise PortfolioArchitectDataError(f"summary.provider_investment_cash.{key} is invalid")
        try:
            parsed = float(value)
        except (TypeError, ValueError) as err:
            raise PortfolioArchitectDataError(f"summary.provider_investment_cash.{key} is invalid") from err
        if not math.isfinite(parsed) or parsed < minimum or parsed > MAX_MONEY_EUR:
            raise PortfolioArchitectDataError(f"summary.provider_investment_cash.{key} is invalid")
        return parsed

    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}] is invalid")
        allowed = {
            "provider_id", "provider_name", "available_eur", "remaining_eur", "as_of",
            "account_balance_eur", "eligible_eur", "authorized_eur",
            "authorization_policy", "authorization_cap_eur",
        }
        if not set(item).issubset(allowed) or not {
            "provider_id", "provider_name", "available_eur", "remaining_eur"
        }.issubset(item):
            raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}] has unexpected fields")
        provider_id = item.get("provider_id")
        if not isinstance(provider_id, str) or _EXECUTION_PROVIDER_RE.fullmatch(provider_id) is None or provider_id in seen:
            raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}].provider_id is invalid")
        seen.add(provider_id)
        provider_name = item.get("provider_name")
        if (
            not isinstance(provider_name, str) or not provider_name.strip()
            or len(provider_name.strip()) > 80 or any(ord(char) < 32 for char in provider_name)
        ):
            raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}].provider_name is invalid")
        available = number(item, "available_eur")
        remaining = number(item, "remaining_eur")
        assert available is not None
        assert remaining is not None
        if remaining > available + 0.01:
            raise PortfolioArchitectDataError(
                f"summary.provider_investment_cash[{index}].remaining_eur exceeds available cash"
            )
        as_of = None
        raw_as_of = item.get("as_of")
        if raw_as_of is not None:
            if not isinstance(raw_as_of, str) or len(raw_as_of) > 64:
                raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}].as_of is invalid")
            try:
                as_of = datetime.fromisoformat(raw_as_of.replace("Z", "+00:00"))
            except ValueError as err:
                raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}].as_of is invalid") from err
            if as_of.tzinfo is None or as_of.utcoffset() is None:
                raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}].as_of must include timezone")
        account = number(item, "account_balance_eur", minimum=-MAX_MONEY_EUR)
        eligible = number(item, "eligible_eur")
        authorized = number(item, "authorized_eur")
        policy = item.get("authorization_policy")
        cap = number(item, "authorization_cap_eur")
        rich = any(value is not None for value in (account, eligible, authorized, policy, cap))
        if rich:
            if account is None or eligible is None or authorized is None or policy not in {"all_available", "capped"}:
                raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}] authorization metadata is incomplete")
            if authorized > eligible + 0.01 or not math.isclose(authorized, available, rel_tol=0, abs_tol=0.01):
                raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}] authorization values are inconsistent")
            if policy == "all_available":
                if cap is not None or not math.isclose(authorized, eligible, rel_tol=0, abs_tol=0.01):
                    raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}] all-available authorization is inconsistent")
            elif cap is None or not math.isclose(authorized, min(eligible, cap), rel_tol=0, abs_tol=0.01):
                raise PortfolioArchitectDataError(f"summary.provider_investment_cash[{index}] capped authorization is inconsistent")
        result.append(ProviderInvestmentCashData(
            provider_id=provider_id,
            provider_name=provider_name.strip(),
            available_eur=available,
            remaining_eur=remaining,
            as_of=as_of,
            account_balance_eur=account,
            eligible_eur=eligible,
            authorized_eur=authorized,
            authorization_policy=policy,
            authorization_cap_eur=cap,
        ))
    return tuple(sorted(result, key=lambda item: item.provider_id))


def _parse_funding_transfers(raw: Any) -> tuple[FundingTransferData, ...]:
    """Validate the bounded advisory funding-transfer plan."""

    if not isinstance(raw, list) or len(raw) > 32:
        raise PortfolioArchitectDataError("summary.funding_transfers must be a bounded list")
    seen: set[tuple[str, str]] = set()
    result: list[FundingTransferData] = []
    required = {
        "from_provider",
        "from_provider_name",
        "to_provider",
        "to_provider_name",
        "amount_eur",
        "fee_eur",
        "settlement_business_days",
    }
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) != required:
            raise PortfolioArchitectDataError(f"summary.funding_transfers[{index}] is invalid")
        source = item.get("from_provider")
        destination = item.get("to_provider")
        if (
            not isinstance(source, str)
            or _EXECUTION_PROVIDER_RE.fullmatch(source) is None
            or not isinstance(destination, str)
            or _EXECUTION_PROVIDER_RE.fullmatch(destination) is None
            or source == destination
            or (source, destination) in seen
        ):
            raise PortfolioArchitectDataError(
                f"summary.funding_transfers[{index}] provider relationship is invalid"
            )
        seen.add((source, destination))
        names: list[str] = []
        for key in ("from_provider_name", "to_provider_name"):
            value = item.get(key)
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value.strip()) > 80
                or any(ord(char) < 32 for char in value)
            ):
                raise PortfolioArchitectDataError(
                    f"summary.funding_transfers[{index}].{key} is invalid"
                )
            names.append(value.strip())
        amount = item.get("amount_eur")
        fee = item.get("fee_eur")
        try:
            amount_value = float(amount)
            fee_value = float(fee)
        except (TypeError, ValueError) as err:
            raise PortfolioArchitectDataError(
                f"summary.funding_transfers[{index}] money value is invalid"
            ) from err
        if (
            not math.isfinite(amount_value)
            or not 0 < amount_value <= MAX_MONEY_EUR
            or not math.isfinite(fee_value)
            or not 0 <= fee_value <= MAX_MONEY_EUR
        ):
            raise PortfolioArchitectDataError(
                f"summary.funding_transfers[{index}] money value is invalid"
            )
        days = item.get("settlement_business_days")
        if isinstance(days, bool) or not isinstance(days, int) or not 0 <= days <= 30:
            raise PortfolioArchitectDataError(
                f"summary.funding_transfers[{index}].settlement_business_days is invalid"
            )
        result.append(
            FundingTransferData(
                from_provider=source,
                from_provider_name=names[0],
                to_provider=destination,
                to_provider_name=names[1],
                amount_eur=amount_value,
                fee_eur=fee_value,
                settlement_business_days=days,
            )
        )
    return tuple(sorted(result, key=lambda item: (item.from_provider, item.to_provider)))


def _parse_monthly_plan(
    summary: dict[str, Any],
    positions: dict[str, PositionData],
) -> MonthlyPlanData:
    """Validate and cross-check the recurring investment plan."""
    contribution = _summary_float(
        summary,
        "monthly_contribution_eur",
        minimum=0,
        maximum=MAX_MONTHLY_CONTRIBUTION_EUR,
    )
    recommended = _summary_float(
        summary,
        "recommended_total_eur",
        minimum=0,
        maximum=MAX_MONEY_EUR,
    )
    execution_present = _EXECUTION_SUMMARY_KEYS.intersection(summary)
    if execution_present and execution_present != _EXECUTION_SUMMARY_KEYS:
        raise PortfolioArchitectDataError("summary contains an incomplete execution contract")
    available_reserve = (
        _summary_float(summary, "available_investment_reserve_eur", minimum=0, maximum=MAX_MONEY_EUR)
        if execution_present else contribution
    )
    funding_present = _FUNDING_SUMMARY_KEYS.intersection(summary)
    if funding_present and funding_present != _FUNDING_SUMMARY_KEYS:
        raise PortfolioArchitectDataError("summary contains an incomplete funding topology contract")
    provider_investment_cash: tuple[ProviderInvestmentCashData, ...] = ()
    funding_transfers: tuple[FundingTransferData, ...] = ()
    estimated_funding_transfer_fees = 0.0
    estimated_total_execution_costs = 0.0
    funding_transfer_count = 0
    if funding_present:
        if not execution_present:
            raise PortfolioArchitectDataError("summary funding topology requires execution metadata")
        provider_investment_cash = _parse_provider_investment_cash(summary.get("provider_investment_cash"))
        funding_transfers = _parse_funding_transfers(summary.get("funding_transfers"))
        source_count = summary.get("provider_investment_cash_source_count")
        if isinstance(source_count, bool) or not isinstance(source_count, int) or source_count != len(provider_investment_cash):
            raise PortfolioArchitectDataError("summary.provider_investment_cash_source_count is inconsistent")
        estimated_funding_transfer_fees = _summary_float(summary, "estimated_funding_transfer_fees_eur", minimum=0, maximum=MAX_MONEY_EUR)
        estimated_total_execution_costs = _summary_float(summary, "estimated_total_execution_costs_eur", minimum=0, maximum=MAX_MONEY_EUR)
        funding_transfer_count = summary.get("funding_transfer_count")
        if isinstance(funding_transfer_count, bool) or not isinstance(funding_transfer_count, int) or not 0 <= funding_transfer_count <= 32:
            raise PortfolioArchitectDataError("summary.funding_transfer_count is invalid")
        if funding_transfer_count != len(funding_transfers):
            raise PortfolioArchitectDataError("summary.funding_transfer_count is inconsistent")
    cash_authorization_present = _CASH_AUTHORIZATION_KEYS.intersection(summary)
    if cash_authorization_present and cash_authorization_present != _CASH_AUTHORIZATION_KEYS:
        raise PortfolioArchitectDataError("summary contains an incomplete investment cash authorization contract")
    investment_account_balance = None
    eligible_investment_cash = None
    authorized_investment_cash = None
    cash_authorization_policy = None
    cash_authorization_cap = None
    if cash_authorization_present:
        investment_account_balance = _summary_float(
            summary, "investment_account_balance_eur", minimum=-MAX_MONEY_EUR, maximum=MAX_MONEY_EUR
        )
        eligible_investment_cash = _summary_float(
            summary, "eligible_investment_cash_eur", minimum=0, maximum=MAX_MONEY_EUR
        )
        authorized_investment_cash = _summary_float(
            summary, "authorized_investment_cash_eur", minimum=0, maximum=MAX_MONEY_EUR
        )
        cash_authorization_policy = summary.get("investment_cash_authorization_policy")
        if cash_authorization_policy not in {"all_available", "capped"}:
            raise PortfolioArchitectDataError("summary.investment_cash_authorization_policy is invalid")
        cap_raw = summary.get("investment_cash_authorization_cap_eur")
        if cap_raw is not None:
            cash_authorization_cap = _summary_float(
                summary, "investment_cash_authorization_cap_eur", minimum=0, maximum=MAX_MONEY_EUR
            )
        if authorized_investment_cash > eligible_investment_cash + 0.01:
            raise PortfolioArchitectDataError("summary authorized investment cash exceeds eligible cash")
        if cash_authorization_policy == "all_available":
            if cash_authorization_cap is not None or not math.isclose(
                authorized_investment_cash, eligible_investment_cash, rel_tol=0, abs_tol=0.01
            ):
                raise PortfolioArchitectDataError("summary all-available investment cash authorization is inconsistent")
        else:
            if cash_authorization_cap is None or not math.isclose(
                authorized_investment_cash, min(eligible_investment_cash, cash_authorization_cap), rel_tol=0, abs_tol=0.01
            ):
                raise PortfolioArchitectDataError("summary capped investment cash authorization is inconsistent")

    if not execution_present and recommended > contribution + 0.01:
        raise PortfolioArchitectDataError(
            "summary.recommended_total_eur exceeds the contribution"
        )
    calculated_recommended = sum(
        position.proposed_buy_eur for position in positions.values()
    )
    if not math.isclose(recommended, calculated_recommended, rel_tol=0, abs_tol=0.01):
        raise PortfolioArchitectDataError(
            "summary.recommended_total_eur is inconsistent with recommendations"
        )

    calculated_cash_outlay = sum(
        position.estimated_cash_outlay_eur
        for position in positions.values()
        if position.proposed_buy_eur > 0
    )
    if execution_present and calculated_cash_outlay > available_reserve + 0.01:
        raise PortfolioArchitectDataError(
            "recommendation cash outlay exceeds the available investment reserve"
        )
    calculated_unallocated = available_reserve - (
        calculated_cash_outlay if execution_present else recommended
    )
    calculated_count = sum(
        1 for position in positions.values() if position.proposed_buy_eur > 0
    )
    calculated_deferred = sum(1 for position in positions.values() if position.deferred)
    reserve_unavailable = any(
        position.recommendation_reason == "investment_reserve_unavailable"
        for position in positions.values()
    )
    calculated_ready = (
        (calculated_count > 0 or calculated_deferred > 0) and not reserve_unavailable
        if execution_present
        else abs(calculated_unallocated) <= 0.01
    )

    present = _MONTHLY_PLAN_KEYS.intersection(summary)
    required_legacy = {"monthly_contribution_eur", "recommended_total_eur"}
    if not required_legacy.issubset(summary):
        raise PortfolioArchitectDataError(
            "summary is missing the contribution contract"
        )

    if present - required_legacy:
        if present != _MONTHLY_PLAN_KEYS:
            raise PortfolioArchitectDataError(
                "summary contains an incomplete investment plan contract"
            )
        source_unallocated = _summary_float(
            summary,
            "unallocated_contribution_eur",
            minimum=-0.01,
            maximum=MAX_MONEY_EUR,
        )
        if not math.isclose(
            source_unallocated, calculated_unallocated, rel_tol=0, abs_tol=0.01
        ):
            raise PortfolioArchitectDataError(
                "summary.unallocated_contribution_eur is inconsistent"
            )
        purchase_count = summary.get("purchase_count")
        if isinstance(purchase_count, bool) or not isinstance(purchase_count, int):
            raise PortfolioArchitectDataError("summary.purchase_count must be an integer")
        if purchase_count != calculated_count:
            raise PortfolioArchitectDataError(
                "summary.purchase_count is inconsistent with recommendations"
            )
        ready = summary.get("monthly_plan_ready")
        if not isinstance(ready, bool) or ready != calculated_ready:
            raise PortfolioArchitectDataError(
                "summary.monthly_plan_ready is inconsistent with recommendations"
            )
    else:
        source_unallocated = calculated_unallocated
        purchase_count = calculated_count
        ready = calculated_ready

    plan_present = _PLAN_CONFIGURATION_KEYS.intersection(summary)
    if plan_present and plan_present != _PLAN_CONFIGURATION_KEYS:
        raise PortfolioArchitectDataError(
            "summary contains an incomplete plan configuration contract"
        )
    if plan_present:
        contribution_per_execution = _summary_float(
            summary,
            "contribution_per_execution_eur",
            minimum=0,
            maximum=MAX_MONTHLY_CONTRIBUTION_EUR,
        )
        if not math.isclose(
            contribution_per_execution, contribution, rel_tol=0, abs_tol=0.01
        ):
            raise PortfolioArchitectDataError(
                "summary.contribution_per_execution_eur is inconsistent"
            )
        budget_amount = _summary_float(
            summary,
            "plan_budget_amount_eur",
            minimum=0,
            maximum=MAX_MONTHLY_CONTRIBUTION_EUR,
        )
        budget_basis = summary.get("plan_budget_basis")
        frequency = summary.get("plan_frequency")
        configuration_source = summary.get("plan_configuration_source")
        name = summary.get("plan_name")
        if budget_basis not in PLAN_BUDGET_BASES:
            raise PortfolioArchitectDataError("summary.plan_budget_basis is invalid")
        if frequency not in PLAN_FREQUENCIES:
            raise PortfolioArchitectDataError("summary.plan_frequency is invalid")
        if configuration_source not in PLAN_CONFIGURATION_SOURCES:
            raise PortfolioArchitectDataError(
                "summary.plan_configuration_source is invalid"
            )
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name.strip()) > MAX_NAME_LENGTH
            or any(ord(character) < 32 for character in name)
        ):
            raise PortfolioArchitectDataError("summary.plan_name is invalid")
        executions = summary.get("scheduled_executions_per_period")
        if (
            isinstance(executions, bool)
            or not isinstance(executions, int)
            or not 1 <= executions <= 28
        ):
            raise PortfolioArchitectDataError(
                "summary.scheduled_executions_per_period is invalid"
            )
        expected_contribution = (
            budget_amount
            if budget_basis == "per_execution"
            else round(budget_amount / executions + 1e-12, 2)
        )
        if not math.isclose(
            expected_contribution, contribution, rel_tol=0, abs_tol=0.01
        ):
            raise PortfolioArchitectDataError(
                "summary plan budget is inconsistent with contribution per execution"
            )
    else:
        contribution_per_execution = contribution
        budget_amount = contribution
        budget_basis = "per_period"
        frequency = "monthly"
        executions = 1
        configuration_source = "yaml"
        name = "Investment plan"

    if execution_present:
        remaining_reserve = _summary_float(summary, "remaining_investment_reserve_eur", minimum=0, maximum=MAX_MONEY_EUR)
        if not math.isclose(remaining_reserve, calculated_unallocated, rel_tol=0, abs_tol=0.01):
            raise PortfolioArchitectDataError("summary.remaining_investment_reserve_eur is inconsistent")
        reserve_source = summary.get("investment_reserve_source")
        if reserve_source not in {"contribution", "gateway_balance", "unavailable"}:
            raise PortfolioArchitectDataError("summary.investment_reserve_source is invalid")
        if cash_authorization_present and not funding_present and reserve_source == "gateway_balance" and not math.isclose(
            available_reserve, authorized_investment_cash or 0.0, rel_tol=0, abs_tol=0.01
        ):
            raise PortfolioArchitectDataError("summary available investment reserve disagrees with authorized cash")
        if funding_present and reserve_source == "gateway_balance":
            scoped_total = sum(item.available_eur for item in provider_investment_cash)
            if not math.isclose(available_reserve, scoped_total, rel_tol=0, abs_tol=0.01):
                raise PortfolioArchitectDataError("summary available investment reserve disagrees with provider-scoped cash")
        reserve_as_of_raw = summary.get("investment_reserve_as_of")
        reserve_as_of = None
        if reserve_as_of_raw is not None:
            if not isinstance(reserve_as_of_raw, str):
                raise PortfolioArchitectDataError("summary.investment_reserve_as_of is invalid")
            try:
                reserve_as_of = datetime.fromisoformat(reserve_as_of_raw.replace("Z", "+00:00"))
            except ValueError as err:
                raise PortfolioArchitectDataError("summary.investment_reserve_as_of is invalid") from err
        execution_policy = summary.get("execution_policy")
        if execution_policy not in {"legacy_distribution", "monthly_continuity", "balanced", "efficiency_first"}:
            raise PortfolioArchitectDataError("summary.execution_policy is invalid")
        max_cost_ratio = _summary_float(summary, "max_cost_ratio_pct", minimum=0, maximum=25)
        max_orders = summary.get("max_orders_per_execution")
        max_deferral_periods = summary.get("max_deferral_periods")
        deferred_count = summary.get("deferred_purchase_count")
        if isinstance(max_orders, bool) or not isinstance(max_orders, int) or not 1 <= max_orders <= 32:
            raise PortfolioArchitectDataError("summary.max_orders_per_execution is invalid")
        if (
            isinstance(max_deferral_periods, bool)
            or not isinstance(max_deferral_periods, int)
            or not 0 <= max_deferral_periods <= 24
        ):
            raise PortfolioArchitectDataError("summary.max_deferral_periods is invalid")
        if isinstance(deferred_count, bool) or not isinstance(deferred_count, int) or not 0 <= deferred_count <= 32:
            raise PortfolioArchitectDataError("summary.deferred_purchase_count is invalid")
        if deferred_count != calculated_deferred:
            raise PortfolioArchitectDataError(
                "summary.deferred_purchase_count is inconsistent with recommendations"
            )
        deferred_contribution = _summary_float(summary, "deferred_contribution_eur", minimum=0, maximum=MAX_MONEY_EUR)
        fees = _summary_float(summary, "estimated_transaction_fees_eur", minimum=0, maximum=MAX_MONEY_EUR)
        if funding_present:
            calculated_transfer_fees = sum(
                position.funding_transfer_fee_eur
                for position in positions.values()
                if position.proposed_buy_eur > 0
            )
            if not math.isclose(estimated_funding_transfer_fees, calculated_transfer_fees, rel_tol=0, abs_tol=0.01):
                raise PortfolioArchitectDataError("summary funding-transfer fees are inconsistent with recommendations")
            expected_edges = {
                (position.funding_provider, position.execution_provider)
                for position in positions.values()
                if position.proposed_buy_eur > 0 and position.funding_transfer_required
            }
            if funding_transfer_count != len(expected_edges):
                raise PortfolioArchitectDataError("summary.funding_transfer_count is inconsistent with recommendations")
            transfer_by_edge = {
                (item.from_provider, item.to_provider): item for item in funding_transfers
            }
            if set(transfer_by_edge) != expected_edges:
                raise PortfolioArchitectDataError(
                    "summary funding-transfer plan is inconsistent with recommendations"
                )
            for edge, transfer in transfer_by_edge.items():
                related = [
                    position
                    for position in positions.values()
                    if position.proposed_buy_eur > 0
                    and position.funding_transfer_required
                    and (position.funding_provider, position.execution_provider) == edge
                ]
                expected_amount = sum(
                    position.proposed_buy_eur + position.estimated_fee_eur
                    for position in related
                )
                expected_fee = sum(position.funding_transfer_fee_eur for position in related)
                expected_days = max(
                    (position.funding_transfer_business_days for position in related),
                    default=0,
                )
                if not math.isclose(transfer.amount_eur, expected_amount, rel_tol=0, abs_tol=0.01):
                    raise PortfolioArchitectDataError(
                        "summary funding-transfer amount is inconsistent with recommendations"
                    )
                if not math.isclose(transfer.fee_eur, expected_fee, rel_tol=0, abs_tol=0.01):
                    raise PortfolioArchitectDataError(
                        "summary funding-transfer fee is inconsistent with recommendations"
                    )
                if transfer.settlement_business_days != expected_days:
                    raise PortfolioArchitectDataError(
                        "summary funding-transfer delay is inconsistent with recommendations"
                    )
            if not math.isclose(estimated_total_execution_costs, fees + estimated_funding_transfer_fees, rel_tol=0, abs_tol=0.01):
                raise PortfolioArchitectDataError("summary total execution costs are inconsistent")
            consumed_by_provider: dict[str, float] = {}
            for position in positions.values():
                if position.proposed_buy_eur > 0 and position.funding_provider is not None:
                    consumed_by_provider[position.funding_provider] = (
                        consumed_by_provider.get(position.funding_provider, 0.0)
                        + position.estimated_cash_outlay_eur
                    )
            for item in provider_investment_cash:
                expected_remaining = item.available_eur - consumed_by_provider.get(item.provider_id, 0.0)
                if not math.isclose(item.remaining_eur, expected_remaining, rel_tol=0, abs_tol=0.01):
                    raise PortfolioArchitectDataError(
                        "summary provider-scoped remaining cash is inconsistent with recommendations"
                    )
        cash_outlay = _summary_float(summary, "estimated_cash_outlay_eur", minimum=0, maximum=MAX_MONEY_EUR)
        if not math.isclose(cash_outlay, calculated_cash_outlay, rel_tol=0, abs_tol=0.01):
            raise PortfolioArchitectDataError(
                "summary.estimated_cash_outlay_eur is inconsistent with recommendations"
            )
        if not math.isclose(cash_outlay, recommended + fees + estimated_funding_transfer_fees, rel_tol=0, abs_tol=0.01):
            raise PortfolioArchitectDataError(
                "summary estimated cash outlay is inconsistent with principal and execution/funding fees"
            )

        execution_ux_present = _EXECUTION_UX_KEYS.intersection(summary)
        if execution_ux_present and execution_ux_present != _EXECUTION_UX_KEYS:
            raise PortfolioArchitectDataError(
                "summary contains an incomplete execution UX contract"
            )
        if execution_ux_present:
            execution_state = summary.get("execution_state")
            if execution_state not in EXECUTION_STATES:
                raise PortfolioArchitectDataError("summary.execution_state is invalid")
            additional_cash_required = _summary_float(
                summary,
                "additional_investment_cash_required_eur",
                minimum=0,
                maximum=MAX_MONEY_EUR,
            )
        else:
            if reserve_source == "unavailable":
                execution_state = "reserve_unavailable"
            elif purchase_count > 0:
                execution_state = "ready"
            elif deferred_count > 0:
                execution_state = "deferred_for_cost_efficiency"
            else:
                execution_state = "no_eligible_purchase"
            additional_cash_required = 0.0
    else:
        remaining_reserve = calculated_unallocated
        reserve_source = "contribution"
        reserve_as_of = None
        execution_policy = "legacy_distribution"
        max_cost_ratio = 0.0
        max_orders = 32
        max_deferral_periods = 0
        deferred_count = 0
        deferred_contribution = 0.0
        fees = 0.0
        cash_outlay = recommended
        execution_state = "ready" if ready else "no_eligible_purchase"
        additional_cash_required = 0.0
        provider_investment_cash = ()
        funding_transfers = ()
        estimated_funding_transfer_fees = 0.0
        estimated_total_execution_costs = 0.0
        funding_transfer_count = 0

    return MonthlyPlanData(
        monthly_contribution_eur=contribution,
        contribution_per_execution_eur=contribution_per_execution,
        budget_amount_eur=budget_amount,
        budget_basis=budget_basis,
        frequency=frequency,
        executions_per_period=executions,
        configuration_source=configuration_source,
        name=name.strip(),
        recommended_total_eur=recommended,
        unallocated_contribution_eur=max(0.0, source_unallocated),
        purchase_count=purchase_count,
        ready=ready,
        available_reserve_eur=available_reserve,
        remaining_reserve_eur=remaining_reserve,
        reserve_source=reserve_source,
        reserve_as_of=reserve_as_of,
        investment_account_balance_eur=investment_account_balance,
        eligible_investment_cash_eur=eligible_investment_cash,
        authorized_investment_cash_eur=authorized_investment_cash,
        investment_cash_authorization_policy=cash_authorization_policy,
        investment_cash_authorization_cap_eur=cash_authorization_cap,
        execution_policy=execution_policy,
        max_cost_ratio_pct=max_cost_ratio,
        max_orders_per_execution=max_orders,
        max_deferral_periods=max_deferral_periods,
        deferred_purchase_count=deferred_count,
        deferred_contribution_eur=deferred_contribution,
        estimated_transaction_fees_eur=fees,
        estimated_cash_outlay_eur=cash_outlay,
        execution_state=execution_state,
        additional_investment_cash_required_eur=additional_cash_required,
        provider_investment_cash=provider_investment_cash,
        funding_transfers=funding_transfers,
        estimated_funding_transfer_fees_eur=estimated_funding_transfer_fees,
        estimated_total_execution_costs_eur=estimated_total_execution_costs,
        funding_transfer_count=funding_transfer_count,
    )


def _parse_runtime(summary: dict[str, Any]) -> RuntimeMetadata:
    """Validate runtime metadata while accepting the v0.5 legacy payload."""
    present = _RUNTIME_KEYS.intersection(summary)
    if present and present != _RUNTIME_KEYS:
        raise PortfolioArchitectDataError(
            "summary contains an incomplete runtime metadata contract"
        )

    if not present:
        return RuntimeMetadata(
            payload_schema_version=4,
            engine_version=None,
            generated_at=None,
        )

    schema_version = summary.get("payload_schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise PortfolioArchitectDataError(
            "summary.payload_schema_version must be an integer"
        )
    if schema_version < 1 or schema_version > MAX_SUPPORTED_PAYLOAD_SCHEMA:
        raise PortfolioArchitectDataError(
            f"Unsupported payload schema version: {schema_version}"
        )

    engine_version = summary.get("engine_version")
    if (
        not isinstance(engine_version, str)
        or len(engine_version) > 32
        or _VERSION_RE.fullmatch(engine_version) is None
    ):
        raise PortfolioArchitectDataError("summary.engine_version is invalid")

    generated_at_value = summary.get("generated_at")
    if not isinstance(generated_at_value, str) or len(generated_at_value) > 64:
        raise PortfolioArchitectDataError("summary.generated_at is invalid")
    try:
        generated_at = datetime.fromisoformat(generated_at_value)
    except ValueError as err:
        raise PortfolioArchitectDataError("summary.generated_at is invalid") from err
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise PortfolioArchitectDataError("summary.generated_at must include a timezone")

    return RuntimeMetadata(
        payload_schema_version=schema_version,
        engine_version=engine_version,
        generated_at=generated_at,
    )


def _bounded_optional_text(
    value: Any,
    *,
    field: str,
    maximum: int,
    required: bool = False,
) -> str | None:
    """Validate one optional policy text value without allowing control data."""
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise PortfolioArchitectDataError(f"{field} must be a string")
    cleaned = value.strip()
    if (
        (required and not cleaned)
        or len(cleaned) > maximum
        or any(ord(char) < 32 and char not in "\t\n\r" for char in cleaned)
    ):
        raise PortfolioArchitectDataError(f"{field} is empty, too long, or invalid")
    return cleaned


def _policy_scalar(value: Any, *, field: str) -> Any:
    """Validate a bounded JSON scalar used as an observed or expected value."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number) or abs(number) > MAX_POLICY_NUMERIC_VALUE:
            raise PortfolioArchitectDataError(f"{field} is outside the allowed range")
        return value
    if isinstance(value, str):
        return _bounded_optional_text(value, field=field, maximum=128, required=True)
    raise PortfolioArchitectDataError(f"{field} must be a bounded JSON scalar")


def _normalise_policy_value(rule: str, value: Any) -> Any:
    """Convert policy values to stable translation tokens where appropriate."""
    if value is None:
        return "not_verified"
    if rule == "accumulating_preferred":
        if value is True or value == "accumulating":
            return "accumulating"
        if value is False or value == "distributing":
            return "distributing"
    if rule == "ireland_preferred":
        if value == "IE":
            return "ireland"
        if value == "LU":
            return "luxembourg"
    if rule == "ucits_required":
        return "ucits" if value is True else "not_ucits" if value is False else value
    if rule == "savings_plan_required":
        return "available" if value is True else "unavailable" if value is False else value
    if isinstance(value, bool):
        return "yes" if value else "no"
    return value


def parse_policy_findings(
    value: Any,
    positions: dict[str, PositionData],
) -> dict[str, PolicyFindingData]:
    """Validate policy findings and index them by stable fund/rule key."""
    if value is None:
        value = []
    if not isinstance(value, list):
        raise PortfolioArchitectDataError("policy_findings must be a list")
    if len(value) > MAX_POLICY_FINDINGS:
        raise PortfolioArchitectDataError(
            f"policy_findings may contain at most {MAX_POLICY_FINDINGS} items"
        )

    by_instrument: dict[str, PositionData] = {}
    for position in positions.values():
        by_instrument[position.fund_id] = position
        by_instrument[position.isin] = position

    findings: dict[str, PolicyFindingData] = {}
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise PortfolioArchitectDataError(f"policy_findings[{index}] must be an object")

        rule = _bounded_optional_text(
            raw.get("rule"),
            field=f"policy_findings[{index}].rule",
            maximum=64,
            required=True,
        )
        if rule not in POLICY_RULES:
            raise PortfolioArchitectDataError(f"policy_findings[{index}].rule is invalid")
        severity = _bounded_optional_text(
            raw.get("severity"),
            field=f"policy_findings[{index}].severity",
            maximum=16,
            required=True,
        )
        if severity not in POLICY_SEVERITIES:
            raise PortfolioArchitectDataError(f"policy_findings[{index}].severity is invalid")
        status = _bounded_optional_text(
            raw.get("status"),
            field=f"policy_findings[{index}].status",
            maximum=32,
            required=True,
        )
        if status not in POLICY_STATUSES:
            raise PortfolioArchitectDataError(f"policy_findings[{index}].status is invalid")

        instrument_id = _bounded_optional_text(
            raw.get("instrument_id"),
            field=f"policy_findings[{index}].instrument_id",
            maximum=64,
        )
        position = by_instrument.get(instrument_id or "")
        if position is None:
            raise PortfolioArchitectDataError(
                f"policy_findings[{index}].instrument_id does not match a recommendation"
            )

        exception_id = _bounded_optional_text(
            raw.get("exception_id"),
            field=f"policy_findings[{index}].exception_id",
            maximum=96,
        )
        exception_rationale = _bounded_optional_text(
            raw.get("exception_rationale"),
            field=f"policy_findings[{index}].exception_rationale",
            maximum=MAX_EXCEPTION_RATIONALE_LENGTH,
        )
        def _optional_policy_date(key: str) -> date | None:
            raw_value = _bounded_optional_text(
                raw.get(key),
                field=f"policy_findings[{index}].{key}",
                maximum=16,
            )
            if raw_value is None:
                return None
            try:
                return date.fromisoformat(raw_value)
            except ValueError as err:
                raise PortfolioArchitectDataError(
                    f"policy_findings[{index}].{key} is invalid"
                ) from err

        approved_date = _optional_policy_date("exception_approved_on")
        last_reviewed_date = _optional_policy_date("exception_last_reviewed_on")
        review_date = _optional_policy_date("exception_review_on")
        exception_review_reason = _bounded_optional_text(
            raw.get("exception_review_reason"),
            field=f"policy_findings[{index}].exception_review_reason",
            maximum=96,
        )
        exception_expected_provider = _bounded_optional_text(
            raw.get("exception_expected_provider"),
            field=f"policy_findings[{index}].exception_expected_provider",
            maximum=32,
        )
        exception_observed_provider = _bounded_optional_text(
            raw.get("exception_observed_provider"),
            field=f"policy_findings[{index}].exception_observed_provider",
            maximum=32,
        )

        if status in {"accepted_exception", "review_required"}:
            if exception_id is None or exception_rationale is None:
                raise PortfolioArchitectDataError(
                    f"policy_findings[{index}] exception metadata is incomplete"
                )
            if status == "review_required":
                if (
                    exception_review_reason != "preferred_execution_provider_changed"
                    or exception_expected_provider is None
                ):
                    raise PortfolioArchitectDataError(
                        f"policy_findings[{index}] review-required metadata is incomplete"
                    )
            elif (
                exception_review_reason is not None
                or exception_expected_provider is not None
                or exception_observed_provider is not None
            ):
                raise PortfolioArchitectDataError(
                    f"policy_findings[{index}] accepted exception contains review-only metadata"
                )
        elif (
            exception_id is not None
            or exception_rationale is not None
            or approved_date is not None
            or last_reviewed_date is not None
            or review_date is not None
            or exception_review_reason is not None
            or exception_expected_provider is not None
            or exception_observed_provider is not None
        ):
            raise PortfolioArchitectDataError(
                f"policy_findings[{index}] contains exception metadata for a non-exception"
            )

        finding = PolicyFindingData(
            rule=rule,
            severity=severity,
            status=status,
            instrument_id=instrument_id,
            fund_id=position.fund_id,
            fund_name=position.name,
            message=_bounded_optional_text(
                raw.get("message"),
                field=f"policy_findings[{index}].message",
                maximum=MAX_POLICY_MESSAGE_LENGTH,
                required=True,
            ),
            observed=_policy_scalar(
                raw.get("observed"),
                field=f"policy_findings[{index}].observed",
            ),
            expected=_policy_scalar(
                raw.get("expected"),
                field=f"policy_findings[{index}].expected",
            ),
            exception_id=exception_id,
            exception_rationale=exception_rationale,
            exception_approved_on=approved_date,
            exception_last_reviewed_on=last_reviewed_date,
            exception_review_on=review_date,
            exception_review_reason=exception_review_reason,
            exception_expected_provider=exception_expected_provider,
            exception_observed_provider=exception_observed_provider,
        )
        if finding.key in findings:
            raise PortfolioArchitectDataError(
                f"Duplicate policy finding for {position.fund_id}/{rule}"
            )
        findings[finding.key] = finding

    return findings


def _parse_policy_summary(
    summary: dict[str, Any],
    policy_findings: Any,
    positions: dict[str, PositionData],
    analysis_date: date,
    *,
    require_review_contract: bool,
) -> PolicySummaryData:
    """Validate policy findings and cross-check the engine summary contract."""
    findings = parse_policy_findings(policy_findings, positions)
    values = tuple(findings.values())
    active_failures = {"fail", "review_required"}
    errors = sum(1 for item in values if item.status in active_failures and item.severity == "error")
    warnings = sum(1 for item in values if item.status in active_failures and item.severity == "warning")
    opportunities = sum(1 for item in values if item.status in active_failures and item.severity == "info")
    accepted = sum(1 for item in values if item.status == "accepted_exception")
    reviews_required = sum(1 for item in values if item.status == "review_required")
    mandatory_compliant = errors == 0 and warnings == 0
    status = "non_compliant" if errors else "attention" if warnings or opportunities else "compliant"
    review_dates = sorted(
        item.exception_review_on
        for item in values
        if item.status == "accepted_exception" and item.exception_review_on is not None
    )
    overdue_dates = [item for item in review_dates if item < analysis_date]
    upcoming_dates = [item for item in review_dates if item >= analysis_date]
    next_review = upcoming_dates[0] if upcoming_dates else None
    oldest_overdue_review = overdue_dates[0] if overdue_dates else None
    decision_dates = [
        item.exception_last_reviewed_on or item.exception_approved_on
        for item in values
        if item.status in {"accepted_exception", "review_required"}
        and (item.exception_last_reviewed_on or item.exception_approved_on) is not None
    ]
    last_decision = max(decision_dates) if decision_dates else None

    present = _POLICY_SUMMARY_KEYS.intersection(summary)
    if present:
        if present != _POLICY_SUMMARY_KEYS:
            raise PortfolioArchitectDataError("summary contains an incomplete policy contract")
        expected_values = {
            "policy_checks_evaluated": len(values),
            "policy_error_findings": errors,
            "policy_warning_findings": warnings,
            "policy_opportunity_findings": opportunities,
            "policy_accepted_exceptions": accepted,
            "mandatory_controls_compliant": mandatory_compliant,
            "next_exception_review_on": next_review.isoformat() if next_review else None,
        }
        for key, expected in expected_values.items():
            if summary.get(key) != expected:
                raise PortfolioArchitectDataError(f"summary.{key} is inconsistent with policy_findings")
    if "policy_exception_reviews_required" in summary:
        if summary.get("policy_exception_reviews_required") != reviews_required:
            raise PortfolioArchitectDataError(
                "summary.policy_exception_reviews_required is inconsistent with policy_findings"
            )

    review_present = _POLICY_REVIEW_KEYS.intersection(summary)
    if require_review_contract and review_present != _POLICY_REVIEW_KEYS:
        raise PortfolioArchitectDataError(
            "summary is missing the complete exception review contract"
        )
    if review_present:
        if review_present != _POLICY_REVIEW_KEYS:
            raise PortfolioArchitectDataError("summary contains an incomplete exception review contract")
        review_expected = {
            "exception_review_overdue": bool(overdue_dates),
            "overdue_exception_reviews": len(overdue_dates),
            "oldest_overdue_exception_review_on": (
                oldest_overdue_review.isoformat() if oldest_overdue_review else None
            ),
            "last_exception_decision_on": (
                last_decision.isoformat() if last_decision else None
            ),
        }
        for key, expected in review_expected.items():
            if summary.get(key) != expected:
                raise PortfolioArchitectDataError(f"summary.{key} is inconsistent with policy_findings")

    source_status = summary.get("policy_status")
    if source_status is not None and source_status != status:
        raise PortfolioArchitectDataError("summary.policy_status is inconsistent with policy_findings")
    failed_findings = summary.get("failed_findings")
    if failed_findings is not None and failed_findings != errors + warnings + opportunities:
        raise PortfolioArchitectDataError("summary.failed_findings is inconsistent with policy_findings")
    accepted_findings = summary.get("accepted_exceptions")
    if accepted_findings is not None and accepted_findings != accepted:
        raise PortfolioArchitectDataError("summary.accepted_exceptions is inconsistent with policy_findings")

    return PolicySummaryData(
        status=status,
        checks_evaluated=len(values),
        errors=errors,
        warnings=warnings,
        opportunities=opportunities,
        accepted_exceptions=accepted,
        exception_reviews_required=reviews_required,
        mandatory_controls_compliant=mandatory_compliant,
        next_exception_review_on=next_review,
        review_overdue=bool(overdue_dates),
        overdue_reviews=len(overdue_dates),
        oldest_overdue_review_on=oldest_overdue_review,
        last_exception_decision_on=last_decision,
        findings=findings,
    )


def parse_portfolio_data(
    recommendations: Any,
    summary: Any = None,
    policy_findings: Any = None,
    holdings: Any = None,
) -> PortfolioData:
    """Validate the complete source payload and derive runtime data defensively."""
    if not isinstance(summary, dict):
        raise PortfolioArchitectDataError("summary must be an object")
    positions = parse_recommendations(recommendations)
    runtime = _parse_runtime(summary)
    if runtime.payload_schema_version >= 8:
        parsed_holdings = parse_holdings(holdings, positions)
    else:
        # Legacy payload compatibility: target recommendations were the whole portfolio.
        parsed_holdings = {
            position.fund_id: HoldingData(
                position_id=position.fund_id,
                wkn=position.wkn,
                isin=position.isin,
                name=position.name,
                instrument_type="etf",
                source_type="ETF",
                current_value_eur=position.current_value_eur,
                quantity=None,
                whole_portfolio_pct=position.current_pct,
                strategy_scope="current_plan",
                plan_fund_id=position.fund_id,
                plan_current_pct=position.current_pct,
            )
            for position in positions.values()
            if position.current_value_eur > 0
        }
    allocation = _parse_allocation_summary(
        summary,
        positions,
        parsed_holdings,
        require_complete_contract=runtime.payload_schema_version >= 8,
    )
    coverage = calculate_target_coverage(positions)
    _validate_source_coverage(summary, coverage)
    monthly_plan = _parse_monthly_plan(summary, positions)
    if runtime.payload_schema_version >= 6 and policy_findings is None:
        raise PortfolioArchitectDataError(
            "payload schema 6 requires a policy_findings attribute"
        )
    analysis_date = (
        runtime.generated_at.date() if runtime.generated_at is not None else date.today()
    )
    policy = _parse_policy_summary(
        summary,
        policy_findings,
        positions,
        analysis_date,
        require_review_contract=runtime.payload_schema_version >= 7,
    )
    return PortfolioData(
        positions=positions,
        holdings=parsed_holdings,
        allocation=allocation,
        coverage=coverage,
        monthly_plan=monthly_plan,
        runtime=runtime,
        policy=policy,
    )
