"""Cost-aware execution-route modelling for long-term investment plans."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Final

D = Decimal

POLICY_MONTHLY_CONTINUITY: Final = "monthly_continuity"
POLICY_BALANCED: Final = "balanced"
POLICY_EFFICIENCY_FIRST: Final = "efficiency_first"
EXECUTION_POLICIES: Final = {
    POLICY_MONTHLY_CONTINUITY,
    POLICY_BALANCED,
    POLICY_EFFICIENCY_FIRST,
}

ROUTE_FREE_SAVINGS_PLAN: Final = "free_savings_plan"
ROUTE_PAID_SAVINGS_PLAN: Final = "paid_savings_plan"
ROUTE_MANUAL_ORDER: Final = "manual_order"
ROUTE_UNAVAILABLE: Final = "unavailable"


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Validated execution-policy settings."""

    enabled: bool = False
    policy: str = POLICY_MONTHLY_CONTINUITY
    max_cost_ratio_pct: Decimal = D("1.50")
    max_deferral_periods: int = 3
    max_orders_per_execution: int = 1
    reserve_mode: str = "contribution_only"
    manual_commission_base_eur: Decimal = D("4.90")
    manual_commission_pct: Decimal = D("0.25")
    manual_commission_min_eur: Decimal = D("9.90")
    manual_commission_max_eur: Decimal = D("59.90")
    manual_venue_fee_pct: Decimal = D("0.0025")
    manual_venue_fee_min_eur: Decimal = D("2.50")
    manual_settlement_fee_eur: Decimal = D("2.90")

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> "ExecutionConfig":
        if not raw:
            return cls()
        enabled = raw.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("execution.enabled must be boolean")
        policy = str(raw.get("policy", POLICY_MONTHLY_CONTINUITY))
        if policy not in EXECUTION_POLICIES:
            raise ValueError("execution.policy is invalid")
        reserve_mode = str(raw.get("reserve_mode", "contribution_only"))
        if reserve_mode not in {"contribution_only", "gateway_balance"}:
            raise ValueError("execution.reserve_mode is invalid")

        def money(key: str, default: str, *, maximum: str = "100000") -> Decimal:
            value = D(str(raw.get(key, default)))
            if not value.is_finite() or value < 0 or value > D(maximum):
                raise ValueError(f"execution.{key} is invalid")
            return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)

        def percentage(key: str, default: str, *, maximum: str = "100") -> Decimal:
            value = D(str(raw.get(key, default)))
            if not value.is_finite() or value < 0 or value > D(maximum):
                raise ValueError(f"execution.{key} is invalid")
            return value.quantize(D("0.0001"), rounding=ROUND_HALF_UP)

        def integer(key: str, default: int, *, minimum: int, maximum: int) -> int:
            value = raw.get(key, default)
            if isinstance(value, bool):
                raise ValueError(f"execution.{key} is invalid")
            try:
                parsed = int(value)
            except (TypeError, ValueError) as err:
                raise ValueError(f"execution.{key} is invalid") from err
            if not minimum <= parsed <= maximum:
                raise ValueError(f"execution.{key} is invalid")
            return parsed

        result = cls(
            enabled=enabled,
            policy=policy,
            max_cost_ratio_pct=percentage("max_cost_ratio_pct", "1.50", maximum="25"),
            max_deferral_periods=integer("max_deferral_periods", 3, minimum=0, maximum=24),
            max_orders_per_execution=integer("max_orders_per_execution", 1, minimum=1, maximum=8),
            reserve_mode=reserve_mode,
            manual_commission_base_eur=money("manual_commission_base_eur", "4.90"),
            manual_commission_pct=percentage("manual_commission_pct", "0.25", maximum="10"),
            manual_commission_min_eur=money("manual_commission_min_eur", "9.90"),
            manual_commission_max_eur=money("manual_commission_max_eur", "59.90"),
            manual_venue_fee_pct=percentage("manual_venue_fee_pct", "0.0025", maximum="10"),
            manual_venue_fee_min_eur=money("manual_venue_fee_min_eur", "2.50"),
            manual_settlement_fee_eur=money("manual_settlement_fee_eur", "2.90"),
        )
        if result.manual_commission_max_eur < result.manual_commission_min_eur:
            raise ValueError("execution manual commission maximum is below its minimum")
        return result


@dataclass(frozen=True, slots=True)
class RouteEstimate:
    route: str
    order_amount_eur: Decimal
    fee_eur: Decimal
    cash_outlay_eur: Decimal
    cost_ratio_pct: Decimal


def estimate_manual_order(amount: Decimal, config: ExecutionConfig) -> RouteEstimate:
    """Estimate one configurable manual-order fee."""
    if amount <= 0:
        return RouteEstimate(ROUTE_MANUAL_ORDER, D("0"), D("0"), D("0"), D("0"))
    commission = config.manual_commission_base_eur + amount * config.manual_commission_pct / D("100")
    commission = min(max(commission, config.manual_commission_min_eur), config.manual_commission_max_eur)
    venue = max(config.manual_venue_fee_min_eur, amount * config.manual_venue_fee_pct / D("100"))
    fee = (commission + venue + config.manual_settlement_fee_eur).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    ratio = (fee / amount * D("100")).quantize(D("0.000001"), rounding=ROUND_HALF_UP)
    cash_outlay = (amount + fee).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    return RouteEstimate(ROUTE_MANUAL_ORDER, amount, fee, cash_outlay, ratio)


def estimate_savings_plan(amount: Decimal, fee_pct: Decimal) -> RouteEstimate:
    if amount <= 0:
        return RouteEstimate(ROUTE_UNAVAILABLE, D("0"), D("0"), D("0"), D("0"))
    fee = (amount * fee_pct / D("100")).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    ratio = fee_pct.quantize(D("0.000001"), rounding=ROUND_HALF_UP)
    route = ROUTE_FREE_SAVINGS_PLAN if fee_pct == 0 else ROUTE_PAID_SAVINGS_PLAN
    cash_outlay = (amount + fee).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    return RouteEstimate(route, amount, fee, cash_outlay, ratio)


def savings_plan_fee_pct(broker: dict[str, Any], isin: str) -> Decimal | None:
    """Return a validated configured savings-plan fee, or None when unavailable."""
    broker_map = broker.get("broker") if isinstance(broker, dict) else None
    plans = broker_map.get("savings_plans") if isinstance(broker_map, dict) else None
    item = plans.get(isin) if isinstance(plans, dict) else None
    if not isinstance(item, dict) or item.get("available") is not True:
        return None
    value = D(str(item.get("fee_pct")))
    if not value.is_finite() or value < 0 or value > D("25"):
        raise ValueError(f"broker savings-plan fee for {isin} is invalid")
    return value


def choose_route(
    *,
    isin: str,
    savings_plan_amount_eur: Decimal,
    manual_order_amount_eur: Decimal,
    broker: dict[str, Any],
    config: ExecutionConfig,
) -> RouteEstimate:
    """Choose the lowest-ratio configured route for one instrument.

    Savings-plan amounts are bounded by the current execution budget. Manual
    orders may use an accumulated dedicated reserve because their fixed/minimum
    costs become less significant as the order grows.
    """
    candidates: list[RouteEstimate] = []
    fee_pct = savings_plan_fee_pct(broker, isin)
    if fee_pct is not None and savings_plan_amount_eur > 0:
        candidates.append(estimate_savings_plan(savings_plan_amount_eur, fee_pct))
    if manual_order_amount_eur > 0:
        candidates.append(estimate_manual_order(manual_order_amount_eur, config))
    candidates = [item for item in candidates if item.order_amount_eur > 0]
    if not candidates:
        return RouteEstimate(ROUTE_UNAVAILABLE, D("0"), D("0"), D("0"), D("0"))
    return min(
        candidates,
        key=lambda item: (
            item.cost_ratio_pct,
            -item.order_amount_eur,
            item.fee_eur,
            item.route,
        ),
    )


def maximum_savings_plan_order_for_cash(
    cash_available_eur: Decimal, fee_pct: Decimal
) -> Decimal:
    """Return the maximum whole-cent savings-plan principal funded by cash."""
    if cash_available_eur <= 0:
        return D("0")
    divisor = D("1") + fee_pct / D("100")
    if divisor <= 0:
        return D("0")
    cents = (cash_available_eur / divisor).quantize(D("0.01"), rounding="ROUND_DOWN")
    while cents > 0 and estimate_savings_plan(cents, fee_pct).cash_outlay_eur > cash_available_eur:
        cents -= D("0.01")
    while estimate_savings_plan(cents + D("0.01"), fee_pct).cash_outlay_eur <= cash_available_eur:
        cents += D("0.01")
    return max(D("0"), cents)


def maximum_manual_order_for_cash(
    cash_available_eur: Decimal, config: ExecutionConfig
) -> Decimal:
    """Return the maximum whole-cent manual-order principal funded by cash."""
    if cash_available_eur <= 0:
        return D("0")
    low = D("0")
    high = cash_available_eur.quantize(D("0.01"), rounding="ROUND_DOWN")
    for _ in range(48):
        midpoint = ((low + high) / D("2")).quantize(D("0.01"), rounding="ROUND_DOWN")
        if midpoint <= low:
            break
        if estimate_manual_order(midpoint, config).cash_outlay_eur <= cash_available_eur:
            low = midpoint
        else:
            high = midpoint
    while low > 0 and estimate_manual_order(low, config).cash_outlay_eur > cash_available_eur:
        low -= D("0.01")
    return max(D("0"), low.quantize(D("0.01"), rounding="ROUND_DOWN"))


def efficient_manual_cash_required(config: ExecutionConfig) -> Decimal:
    """Return cash required for the smallest cost-efficient manual order."""
    minimum = efficient_manual_order_minimum(config)
    return estimate_manual_order(minimum, config).cash_outlay_eur


def efficient_manual_order_minimum(config: ExecutionConfig) -> Decimal:
    """Return the smallest whole-cent manual order meeting the cost ceiling.

    A bounded binary search is deterministic and covers tiered minimum/maximum fees.
    """
    if config.max_cost_ratio_pct <= 0:
        return D("0")
    low = D("0.01")
    high = D("10000000")
    if estimate_manual_order(high, config).cost_ratio_pct > config.max_cost_ratio_pct:
        return high
    for _ in range(48):
        midpoint = ((low + high) / D("2")).quantize(D("0.01"), rounding=ROUND_HALF_UP)
        if midpoint <= low:
            break
        if estimate_manual_order(midpoint, config).cost_ratio_pct <= config.max_cost_ratio_pct:
            high = midpoint
        else:
            low = midpoint
    return high.quantize(D("0.01"), rounding=ROUND_HALF_UP)
