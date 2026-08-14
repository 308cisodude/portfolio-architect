from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any

from .execution import (
    ExecutionConfig,
    POLICY_BALANCED,
    POLICY_EFFICIENCY_FIRST,
    ROUTE_MANUAL_ORDER,
    ROUTE_UNAVAILABLE,
    choose_route,
    efficient_manual_cash_required,
    estimate_savings_plan,
    maximum_manual_order_for_cash,
    maximum_savings_plan_order_for_cash,
    savings_plan_fee_pct,
)
from .identity import build_position_identity_index, match_position_for_target
from .models import Position, Recommendation

D = Decimal
_MAX_FUNDS = 32
_FUND_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")


def round_to_step(amount: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return amount.quantize(D("0.01"), rounding=ROUND_HALF_UP)
    return (amount / step).quantize(D("1"), rounding=ROUND_HALF_UP) * step


def floor_to_step(amount: Decimal, step: Decimal) -> Decimal:
    """Round a funded order down so fees can never overdraw the reserve."""
    if step <= 0:
        return amount.quantize(D("0.01"), rounding="ROUND_DOWN")
    return (amount // step) * step


def _allocation_status(deviation_pp: Decimal, corridor_pp: Decimal) -> str:
    if deviation_pp < -corridor_pp:
        return "underweight"
    if deviation_pp > corridor_pp:
        return "overweight"
    return "on_target"


def _validate_funds(funds: Any) -> list[dict[str, Any]]:
    """Validate configured plan positions and return positive-weight targets.

    Zero-weight entries from older configurations are accepted for backward
    compatibility but are outside the current plan scope. They do not receive a
    synthetic zero target, drift status, policy check, or purchase recommendation.
    """
    if not isinstance(funds, list) or not funds:
        raise ValueError("portfolio.allocation must be a non-empty list")
    if len(funds) > _MAX_FUNDS:
        raise ValueError(f"portfolio.allocation may contain at most {_MAX_FUNDS} funds")

    seen_ids: set[str] = set()
    seen_wkns: set[str] = set()
    seen_isins: set[str] = set()
    validated: list[dict[str, Any]] = []

    for index, raw_fund in enumerate(funds):
        if not isinstance(raw_fund, dict):
            raise ValueError(f"portfolio.allocation[{index}] must be a mapping")
        fund = dict(raw_fund)
        fund_id = fund.get("id")
        if not isinstance(fund_id, str) or not _FUND_ID_RE.fullmatch(fund_id):
            raise ValueError(f"portfolio.allocation[{index}].id must match {_FUND_ID_RE.pattern}")
        if fund_id in seen_ids:
            raise ValueError(f"Duplicate fund id: {fund_id}")
        seen_ids.add(fund_id)

        for key, seen, maximum in (("wkn", seen_wkns, 16), ("isin", seen_isins, 32)):
            value = fund.get(key)
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
                raise ValueError(f"portfolio.allocation[{index}].{key} must be a non-empty bounded string")
            value = value.strip().upper()
            if value in seen:
                raise ValueError(f"Duplicate {key}: {value}")
            seen.add(value)
            fund[key] = value

        name = fund.get("name")
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name.strip()) > 160
            or any(ord(char) < 32 for char in name)
        ):
            raise ValueError(f"portfolio.allocation[{index}].name must be printable and at most 160 characters")
        fund["name"] = name.strip()

        target = D(str(fund.get("target_pct")))
        if not target.is_finite() or target < 0 or target > 100:
            raise ValueError(f"portfolio.allocation[{index}].target_pct must be between 0 and 100")
        if not isinstance(fund.get("buy_enabled", True), bool):
            raise ValueError(f"portfolio.allocation[{index}].buy_enabled must be boolean")
        fund["target_pct"] = target
        if target > 0:
            validated.append(fund)

    if not validated:
        raise ValueError("At least one positive-weight current-plan position is required")
    target_sum = sum(fund["target_pct"] for fund in validated)
    if target_sum != D("100"):
        raise ValueError(f"Positive target weights must sum to 100%, got {target_sum}%")
    return validated


def target_funds(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validated positive-weight positions in the current plan scope."""
    return _validate_funds(document["portfolio"]["allocation"])


def _legacy_proposals(
    *,
    funds: list[dict[str, Any]],
    monthly: Decimal,
    minimum: Decimal,
    step: Decimal,
    deviation_pp: dict[str, Decimal],
    need: dict[str, Decimal],
) -> dict[str, Decimal]:
    """Return the established allocation algorithm unchanged."""
    buyable_funds = [fund for fund in funds if fund.get("buy_enabled", True)]
    total_need = sum(need.values())
    eligible_target_sum = sum(fund["target_pct"] for fund in buyable_funds)
    raw: dict[str, Decimal] = {}
    for fund in funds:
        wkn = fund["wkn"]
        if not fund.get("buy_enabled", True):
            raw[wkn] = D("0")
        elif total_need:
            raw[wkn] = monthly * need[wkn] / total_need
        else:
            raw[wkn] = monthly * fund["target_pct"] / eligible_target_sum

    proposed = {wkn: round_to_step(value, step) for wkn, value in raw.items()}
    proposed = {wkn: (value if value >= minimum else D("0")) for wkn, value in proposed.items()}
    residual = monthly - sum(proposed.values())
    order = sorted(
        buyable_funds,
        key=lambda fund: (deviation_pp[fund["wkn"]], -fund["target_pct"]),
    )
    guard = 0
    while abs(residual) >= step and guard < 10000:
        changed = False
        candidates = order if residual > 0 else list(reversed(order))
        for fund in candidates:
            wkn = fund["wkn"]
            candidate = proposed[wkn] + (step if residual > 0 else -step)
            if candidate < 0 or (D("0") < candidate < minimum):
                continue
            proposed[wkn] = candidate
            residual += -step if residual > 0 else step
            changed = True
            break
        if not changed:
            break
        guard += 1
    if residual and order:
        proposed[order[0]["wkn"]] += residual
    return proposed


def allocate_buys(
    positions: dict[str, Position],
    document: dict[str, Any],
    *,
    broker: dict[str, Any] | None = None,
    execution: dict[str, Any] | None = None,
    available_reserve_eur: Decimal | None = None,
) -> list[Recommendation]:
    """Calculate allocation and cost-aware buy recommendations.

    The legacy monthly distribution remains the default. Cost-aware execution is
    activated explicitly and then limits recommendations to the configured number
    of orders, chooses the cheapest configured execution route, and may defer an
    inefficient purchase without changing the allocation diagnostics.
    """
    portfolio = document["portfolio"]
    rules = document["rebalancing"]
    funds = _validate_funds(portfolio["allocation"])
    monthly = D(str(portfolio["monthly_contribution"]))
    corridor = D(str(rules.get("corridor_pp", 1)))
    minimum = D(str(rules.get("minimum_trade", 20)))
    step = D(str(rules.get("rounding_step", 10)))
    execution_config = ExecutionConfig.from_mapping(execution)
    identity_index = build_position_identity_index(positions.values())
    matched_positions = {
        fund["wkn"]: match_position_for_target(fund, identity_index)
        for fund in funds
    }

    for field, value in (
        ("monthly_contribution", monthly),
        ("corridor_pp", corridor),
        ("minimum_trade", minimum),
        ("rounding_step", step),
    ):
        if not value.is_finite() or value < 0:
            raise ValueError(f"{field} must be a finite non-negative number")
    if step == 0:
        raise ValueError("rounding_step must be greater than zero")

    values: dict[str, Decimal] = {}
    for fund in funds:
        imported = matched_positions[fund["wkn"]]
        value = imported.value_eur if imported is not None else D("0")
        if not value.is_finite() or value < 0:
            raise ValueError(f"Position value for {fund['wkn']} must be non-negative")
        values[fund["wkn"]] = value

    plan_total = sum(values.values())
    whole_total = sum(position.value_eur for position in positions.values())
    buyable_funds = [fund for fund in funds if fund.get("buy_enabled", True)]
    if not buyable_funds:
        raise ValueError("At least one fund must have buy_enabled=true")

    reserve_unavailable = (
        execution_config.enabled
        and execution_config.reserve_mode == "gateway_balance"
        and available_reserve_eur is None
    )
    reserve = monthly
    if execution_config.enabled and execution_config.reserve_mode == "gateway_balance":
        reserve = D("0") if available_reserve_eur is None else D(str(available_reserve_eur))
    if not reserve.is_finite() or reserve < 0:
        raise ValueError("available investment reserve must be finite and non-negative")

    projection_budget = reserve if execution_config.enabled else monthly
    projected_total = plan_total + (projection_budget if projection_budget > 0 else monthly)
    if projected_total <= 0:
        raise ValueError("Projected current-plan value must be positive")

    pct: dict[str, Decimal] = {}
    whole_pct: dict[str, Decimal] = {}
    deviation_pp: dict[str, Decimal] = {}
    target_value: dict[str, Decimal] = {}
    deviation_eur: dict[str, Decimal] = {}
    status: dict[str, str] = {}
    need: dict[str, Decimal] = {}
    execution_need: dict[str, Decimal] = {}

    for fund in funds:
        wkn = fund["wkn"]
        target = fund["target_pct"]
        pct[wkn] = values[wkn] / plan_total * D("100") if plan_total else D("0")
        whole_pct[wkn] = values[wkn] / whole_total * D("100") if whole_total else D("0")
        deviation_pp[wkn] = pct[wkn] - target
        target_value[wkn] = plan_total * target / D("100")
        deviation_eur[wkn] = values[wkn] - target_value[wkn]
        status[wkn] = _allocation_status(deviation_pp[wkn], corridor)
        required = projected_total * target / D("100") - values[wkn]
        execution_need[wkn] = (
            max(D("0"), required) if fund.get("buy_enabled", True) else D("0")
        )
        need[wkn] = (
            execution_need[wkn]
            if status[wkn] == "underweight"
            else D("0")
        )

    proposed = {fund["wkn"]: D("0") for fund in funds}
    routes = {fund["wkn"]: "legacy" for fund in funds}
    fees = {fund["wkn"]: D("0") for fund in funds}
    cash_outlays = {fund["wkn"]: D("0") for fund in funds}
    ratios = {fund["wkn"]: D("0") for fund in funds}
    reasons = {fund["wkn"]: "no_purchase_for_" + status[fund["wkn"]] for fund in funds}
    additional = {fund["wkn"]: D("0") for fund in funds}
    deferred = {fund["wkn"]: False for fund in funds}

    if not execution_config.enabled:
        proposed = _legacy_proposals(
            funds=funds,
            monthly=monthly,
            minimum=minimum,
            step=step,
            deviation_pp=deviation_pp,
            need=need,
        )
        for fund in funds:
            wkn = fund["wkn"]
            if proposed[wkn] > 0:
                reasons[wkn] = f"purchase_for_{status[wkn]}"
                cash_outlays[wkn] = proposed[wkn]
    else:
        broker_document = broker if isinstance(broker, dict) else {}
        ranked = sorted(
            buyable_funds,
            key=lambda fund: (
                0 if status[fund["wkn"]] == "underweight" else 1,
                deviation_pp[fund["wkn"]],
                -fund["target_pct"],
                fund["id"],
            ),
        )
        if reserve_unavailable:
            fund = ranked[0]
            wkn = fund["wkn"]
            routes[wkn] = ROUTE_UNAVAILABLE
            deferred[wkn] = True
            reasons[wkn] = "investment_reserve_unavailable"
        else:
            remaining_reserve = reserve
            remaining_periodic_budget = min(monthly, reserve)
            remaining_funds = list(ranked)
            completed_orders = 0

            while (
                completed_orders < execution_config.max_orders_per_execution
                and remaining_reserve >= minimum
                and remaining_funds
            ):
                candidates: list[tuple[dict[str, Any], Any]] = []
                for fund in remaining_funds:
                    wkn = fund["wkn"]
                    desired = min(remaining_reserve, execution_need[wkn])
                    if desired <= 0:
                        continue
                    rounded_desired = floor_to_step(desired, step)
                    manual_amount = floor_to_step(
                        min(
                            rounded_desired,
                            maximum_manual_order_for_cash(
                                remaining_reserve, execution_config
                            ),
                        ),
                        step,
                    )
                    configured_savings_fee = savings_plan_fee_pct(
                        broker_document, fund["isin"]
                    )
                    savings_amount = D("0")
                    if configured_savings_fee is not None:
                        # A Comdirect savings-plan rate is the total cash debit.
                        # The percentage fee is contained in that rate, so derive
                        # the maximum invested principal from the remaining gross
                        # periodic cash budget instead of adding the fee on top of
                        # the configured contribution.
                        savings_cash_budget = min(
                            remaining_reserve, remaining_periodic_budget
                        )
                        maximum_savings_principal = maximum_savings_plan_order_for_cash(
                            savings_cash_budget, configured_savings_fee
                        )
                        savings_amount = min(
                            desired, maximum_savings_principal
                        ).quantize(D("0.01"), rounding=ROUND_HALF_UP)
                        while (
                            savings_amount > 0
                            and estimate_savings_plan(
                                savings_amount, configured_savings_fee
                            ).cash_outlay_eur
                            > savings_cash_budget
                        ):
                            savings_amount -= D("0.01")
                    if manual_amount < minimum:
                        manual_amount = D("0")
                    if savings_amount < minimum:
                        savings_amount = D("0")
                    route = choose_route(
                        isin=fund["isin"],
                        savings_plan_amount_eur=savings_amount,
                        manual_order_amount_eur=manual_amount,
                        broker=broker_document,
                        config=execution_config,
                    )
                    if route.route != ROUTE_UNAVAILABLE:
                        candidates.append((fund, route))

                if not candidates:
                    if remaining_funds:
                        reasons[remaining_funds[0]["wkn"]] = "execution_route_unavailable"
                    break

                efficient = [
                    item
                    for item in candidates
                    if item[1].cost_ratio_pct <= execution_config.max_cost_ratio_pct
                ]
                reserve_periods = int(reserve / monthly) if monthly > 0 else 0
                forced_by_limit = (
                    execution_config.policy == POLICY_BALANCED
                    and reserve_periods >= execution_config.max_deferral_periods + 1
                )

                if execution_config.policy not in {POLICY_BALANCED, POLICY_EFFICIENCY_FIRST}:
                    selected_fund, selected_route = candidates[0]
                elif efficient:
                    selected_fund, selected_route = efficient[0]
                elif forced_by_limit:
                    selected_fund, selected_route = candidates[0]
                else:
                    selected_fund, selected_route = candidates[0]
                    wkn = selected_fund["wkn"]
                    routes[wkn] = selected_route.route
                    fees[wkn] = selected_route.fee_eur
                    cash_outlays[wkn] = selected_route.cash_outlay_eur
                    ratios[wkn] = selected_route.cost_ratio_pct
                    deferred[wkn] = True
                    reasons[wkn] = "transaction_cost_threshold_not_met"
                    threshold = efficient_manual_cash_required(execution_config)
                    additional[wkn] = max(D("0"), threshold - reserve).quantize(
                        D("0.01"), rounding=ROUND_HALF_UP
                    )
                    break

                wkn = selected_fund["wkn"]
                amount = min(selected_route.order_amount_eur, remaining_reserve)
                proposed[wkn] = amount.quantize(D("0.01"), rounding=ROUND_HALF_UP)
                routes[wkn] = selected_route.route
                fees[wkn] = selected_route.fee_eur
                cash_outlays[wkn] = selected_route.cash_outlay_eur
                ratios[wkn] = selected_route.cost_ratio_pct
                reasons[wkn] = (
                    "maximum_deferral_reached"
                    if forced_by_limit
                    and selected_route.cost_ratio_pct > execution_config.max_cost_ratio_pct
                    else "most_underweight_cost_efficient"
                )
                remaining_reserve -= selected_route.cash_outlay_eur
                if selected_route.route != ROUTE_MANUAL_ORDER:
                    remaining_periodic_budget = max(
                        D("0"),
                        remaining_periodic_budget - selected_route.cash_outlay_eur,
                    )
                remaining_funds.remove(selected_fund)
                completed_orders += 1

    return [
        Recommendation(
            fund_id=fund["id"],
            wkn=fund["wkn"],
            isin=fund["isin"],
            name=fund["name"],
            target_pct=fund["target_pct"],
            current_value_eur=values[fund["wkn"]],
            target_value_eur=target_value[fund["wkn"]],
            deviation_eur=deviation_eur[fund["wkn"]],
            current_pct=pct[fund["wkn"]],
            whole_portfolio_pct=whole_pct[fund["wkn"]],
            deviation_pp=deviation_pp[fund["wkn"]],
            allocation_status=status[fund["wkn"]],
            buy_enabled=bool(fund.get("buy_enabled", True)),
            proposed_buy_eur=proposed[fund["wkn"]],
            execution_route=routes[fund["wkn"]],
            estimated_fee_eur=fees[fund["wkn"]],
            estimated_cash_outlay_eur=cash_outlays[fund["wkn"]],
            estimated_cost_ratio_pct=ratios[fund["wkn"]],
            recommendation_reason=reasons[fund["wkn"]],
            additional_reserve_required_eur=additional[fund["wkn"]],
            deferred=deferred[fund["wkn"]],
            source_ids=(
                matched_positions[fund["wkn"]].source_ids
                if matched_positions[fund["wkn"]] is not None
                else ()
            ),
            source_values_eur=(
                matched_positions[fund["wkn"]].source_values_eur
                if matched_positions[fund["wkn"]] is not None
                else ()
            ),
        )
        for fund in funds
    ]
