"""Provider-neutral portfolio calculation entry point.

The calculation layer has no Home Assistant imports. Source adapters normalize
holdings into canonical positions; this module combines them with the bounded local
YAML configuration and returns the stable schema-8 payload.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
import re
from typing import Any

from . import __version__
from .coverage import calculate_target_coverage
from .identity import (
    build_position_identity_index,
    match_position_for_target,
    normalized_isin,
    normalized_wkn,
)
from .io import load_yaml
from .models import Holding, Position
from .plan import apply_plan_override
from .policy import evaluate
from .execution import ExecutionConfig, choose_route, preferred_execution_route
from .funding import provider_cash_from_metadata
from .rebalance import allocate_buys, target_funds

D = Decimal
_POSITION_ID_RE = re.compile(r"[^a-z0-9]+")
_REQUIRED_CONFIG_FILES = (
    "portfolio.yaml",
    "policy.yaml",
    "instruments.yaml",
    "broker.yaml",
)
_OPTIONAL_CONFIG_FILES = ("exceptions.yaml",)


def _minimum_cash_required_for_next_purchase(
    *,
    recommendations: list[Any],
    portfolio: dict[str, Any],
    broker: dict[str, Any],
    execution_config: dict[str, Any] | None,
    evaluated_on: date | None = None,
) -> Decimal:
    """Return minimum gross cash needed for the next buyable target position."""
    buyable = [item for item in recommendations if item.buy_enabled]
    if not buyable:
        return D("0")
    ranked = sorted(
        buyable,
        key=lambda item: (
            0 if item.allocation_status == "underweight" else 1,
            item.deviation_pp,
            -item.target_pct,
            item.fund_id,
        ),
    )
    minimum_order = D(
        str(portfolio.get("rebalancing", {}).get("minimum_trade", 20))
    )
    if minimum_order <= 0:
        return D("0")
    config = ExecutionConfig.from_mapping(execution_config)
    route = choose_route(
        isin=ranked[0].isin,
        savings_plan_amount_eur=minimum_order,
        manual_order_amount_eur=minimum_order,
        broker=broker,
        config=config,
        evaluated_on=evaluated_on,
    )
    return route.cash_outlay_eur


def configuration_files(config_directory: Path) -> tuple[Path, ...]:
    """Return the bounded configuration files that currently influence a calculation.

    Required documents are always returned so callers can fail closed when one is
    missing. Optional documents participate only while they actually exist; absence
    of ``exceptions.yaml`` is a valid configuration state and must not invalidate
    configuration metadata or last-known-good fingerprints.
    """
    required = tuple(config_directory / name for name in _REQUIRED_CONFIG_FILES)
    optional = tuple(
        path
        for name in _OPTIONAL_CONFIG_FILES
        if (path := config_directory / name).is_file()
    )
    return (*required, *optional)


def validate_configuration_source(config_directory: Path) -> None:
    """Validate the bounded local YAML configuration set."""
    if not config_directory.is_dir():
        raise ValueError("Portfolio configuration directory does not exist")
    for name in _REQUIRED_CONFIG_FILES:
        path = config_directory / name
        if not path.is_file():
            raise ValueError(f"Required portfolio configuration file is missing: {name}")


def calculate_portfolio_payload_from_positions(
    positions: dict[str, Position],
    config_directory: Path,
    *,
    evaluated_at: datetime,
    plan_override: dict[str, Any] | None = None,
    source_provider: str,
    source_label: str,
    source_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate one schema-8 payload from canonical provider-neutral positions."""
    validate_configuration_source(config_directory)
    if not positions:
        raise ValueError("Portfolio source returned no positions")
    timestamp = _normalise_timestamp(evaluated_at)
    analysis_date = timestamp.date()

    portfolio_source = load_yaml(config_directory / "portfolio.yaml")
    portfolio, plan_runtime = apply_plan_override(portfolio_source, plan_override)
    policy = load_yaml(config_directory / "policy.yaml")
    instruments = load_yaml(config_directory / "instruments.yaml")
    broker = load_yaml(config_directory / "broker.yaml")
    exceptions = _load_optional_yaml(config_directory / "exceptions.yaml")
    source_metadata = dict(source_metadata or {})
    execution_config = None
    if isinstance(plan_override, dict):
        execution_config = plan_override.get("execution")
    if execution_config is None:
        execution_config = portfolio.get("execution")
    provider_cash = provider_cash_from_metadata(source_metadata.get("provider_investment_cash"))
    provider_cash_is_execution_reserve = bool(
        provider_cash
        and isinstance(execution_config, dict)
        and execution_config.get("enabled")
        and execution_config.get("reserve_mode", "contribution_only") == "gateway_balance"
    )
    provider_reserve_by_provider = (
        {item.provider_id: item.available_eur for item in provider_cash}
        if provider_cash_is_execution_reserve
        else None
    )
    funding_provider_names = {item.provider_id: item.provider_name for item in provider_cash}
    reserve_value = source_metadata.get("investment_reserve_eur")
    available_reserve = D(str(reserve_value)) if reserve_value is not None else None
    if provider_reserve_by_provider is not None:
        available_reserve = sum(provider_reserve_by_provider.values(), D("0"))
    cash_authorization_present = all(
        key in source_metadata
        for key in (
            "investment_account_balance_eur",
            "eligible_investment_cash_eur",
            "authorized_investment_cash_eur",
            "investment_cash_authorization_policy",
            "investment_cash_authorization_cap_eur",
        )
    )
    recommendations = allocate_buys(
        positions,
        portfolio,
        broker=broker,
        execution=execution_config if isinstance(execution_config, dict) else None,
        available_reserve_eur=available_reserve,
        available_reserve_by_provider=provider_reserve_by_provider,
        funding_provider_names=funding_provider_names,
        evaluated_on=analysis_date,
    )
    holdings = _build_holdings(positions, portfolio, recommendations)
    execution_policy = ExecutionConfig.from_mapping(
        execution_config if isinstance(execution_config, dict) else None
    )
    reference_amount = D(str(portfolio["portfolio"]["monthly_contribution"]))
    preferred_execution_providers: dict[str, str | None] = {}
    for fund in target_funds(portfolio):
        route = preferred_execution_route(
            isin=fund["isin"],
            reference_amount_eur=reference_amount,
            broker=broker,
            config=execution_policy,
            evaluated_on=analysis_date,
        )
        preferred_execution_providers[fund["isin"]] = route.provider_id
    findings = evaluate(
        portfolio,
        policy,
        instruments,
        broker,
        exceptions,
        evaluated_on=analysis_date,
        preferred_execution_providers=preferred_execution_providers,
    )
    coverage = calculate_target_coverage(recommendations)

    failed = [item for item in findings if item.status in {"fail", "review_required"}]
    accepted = [item for item in findings if item.status == "accepted_exception"]
    exception_reviews_required = [
        item for item in findings if item.status == "review_required"
    ]
    policy_errors = [item for item in failed if item.severity == "error"]
    policy_warnings = [item for item in failed if item.severity == "warning"]
    policy_opportunities = [item for item in failed if item.severity == "info"]

    review_dates: list[date] = []
    decision_dates: list[date] = []
    for finding in [*accepted, *exception_reviews_required]:
        for raw_value in (
            finding.exception_last_reviewed_on,
            finding.exception_approved_on,
        ):
            if not raw_value:
                continue
            try:
                decision_dates.append(date.fromisoformat(raw_value))
                break
            except ValueError:
                continue
        if finding.status == "accepted_exception" and finding.exception_review_on:
            try:
                review_dates.append(date.fromisoformat(finding.exception_review_on))
            except ValueError:
                continue

    overdue_review_dates = sorted(value for value in review_dates if value < analysis_date)
    upcoming_review_dates = sorted(value for value in review_dates if value >= analysis_date)
    next_exception_review_on = (
        upcoming_review_dates[0].isoformat() if upcoming_review_dates else None
    )
    oldest_overdue_exception_review_on = (
        overdue_review_dates[0].isoformat() if overdue_review_dates else None
    )
    last_exception_decision_on = (
        max(decision_dates).isoformat() if decision_dates else None
    )

    allocation_counts = {
        state: sum(1 for item in recommendations if item.allocation_status == state)
        for state in ("underweight", "on_target", "overweight")
    }
    contribution_per_execution = D(str(portfolio["portfolio"]["monthly_contribution"]))
    execution_enabled = bool(isinstance(execution_config, dict) and execution_config.get("enabled"))
    reserve_mode = str(execution_config.get("reserve_mode", "contribution_only")) if isinstance(execution_config, dict) else "contribution_only"
    reserve_available = (
        execution_enabled
        and available_reserve is not None
        and reserve_mode == "gateway_balance"
    )
    reserve_required_but_unavailable = (
        execution_enabled and reserve_mode == "gateway_balance" and not reserve_available
    )
    investment_reserve = (
        available_reserve
        if reserve_available
        else (D("0") if reserve_required_but_unavailable else contribution_per_execution)
    )
    recommended_total = sum(item.proposed_buy_eur for item in recommendations)
    estimated_transaction_fees = sum(
        item.estimated_fee_eur
        for item in recommendations
        if item.proposed_buy_eur > 0
    )
    estimated_funding_transfer_fees = sum(
        item.funding_transfer_fee_eur
        for item in recommendations
        if item.proposed_buy_eur > 0
    )
    funding_transfer_count = len({
        (item.funding_provider, item.execution_provider)
        for item in recommendations
        if item.proposed_buy_eur > 0 and item.funding_transfer_required
    })
    provider_remaining = {
        item.provider_id: item.available_eur for item in provider_cash
    }
    transfer_plans: dict[tuple[str, str], dict[str, Any]] = {}
    for item in recommendations:
        if item.proposed_buy_eur <= 0 or item.funding_provider is None:
            continue
        if item.funding_provider in provider_remaining:
            provider_remaining[item.funding_provider] -= item.estimated_cash_outlay_eur
        if not item.funding_transfer_required or item.execution_provider is None:
            continue
        edge = (item.funding_provider, item.execution_provider)
        existing = transfer_plans.get(edge)
        transfer_amount = item.proposed_buy_eur + item.estimated_fee_eur
        if existing is None:
            transfer_plans[edge] = {
                "from_provider": item.funding_provider,
                "from_provider_name": item.funding_provider_name or item.funding_provider,
                "to_provider": item.execution_provider,
                "to_provider_name": item.execution_provider_name or item.execution_provider,
                "amount_eur": transfer_amount,
                "fee_eur": item.funding_transfer_fee_eur,
                "settlement_business_days": item.funding_transfer_business_days,
            }
        else:
            existing["amount_eur"] += transfer_amount
            existing["fee_eur"] += item.funding_transfer_fee_eur
            existing["settlement_business_days"] = max(
                existing["settlement_business_days"],
                item.funding_transfer_business_days,
            )
    estimated_cash_outlay = sum(
        item.estimated_cash_outlay_eur
        for item in recommendations
        if item.proposed_buy_eur > 0
    )
    remaining_reserve = max(D("0"), investment_reserve - estimated_cash_outlay)
    unallocated_contribution = remaining_reserve
    purchase_count = sum(1 for item in recommendations if item.proposed_buy_eur > 0)
    deferred_count = sum(1 for item in recommendations if item.deferred)
    actionable_deferred = any(
        item.deferred and item.recommendation_reason != "investment_reserve_unavailable"
        for item in recommendations
    )

    execution_state = "ready"
    additional_investment_cash_required = D("0")
    if reserve_required_but_unavailable:
        execution_state = "reserve_unavailable"
    elif purchase_count > 0:
        execution_state = "ready"
    elif execution_enabled:
        cost_deferred = [
            item
            for item in recommendations
            if item.deferred
            and item.recommendation_reason == "transaction_cost_threshold_not_met"
        ]
        if cost_deferred:
            execution_state = "deferred_for_cost_efficiency"
            additional_investment_cash_required = min(
                (item.additional_reserve_required_eur for item in cost_deferred),
                default=D("0"),
            )
        else:
            minimum_cash_required = _minimum_cash_required_for_next_purchase(
                recommendations=recommendations,
                portfolio=portfolio,
                broker=broker,
                execution_config=execution_config,
                evaluated_on=analysis_date,
            )
            if minimum_cash_required > investment_reserve + D("0.01"):
                execution_state = "waiting_for_reserve"
                additional_investment_cash_required = (
                    minimum_cash_required - investment_reserve
                ).quantize(D("0.01"))
            else:
                execution_state = "no_eligible_purchase"
    elif abs(unallocated_contribution) > D("0.01"):
        execution_state = "no_eligible_purchase"

    whole_portfolio_value = sum(item.current_value_eur for item in holdings)
    current_plan_value = sum(item.current_value_eur for item in recommendations)
    outside_scope_value = whole_portfolio_value - current_plan_value
    current_plan_whole_pct = current_plan_value / whole_portfolio_value * D("100")
    outside_scope_whole_pct = outside_scope_value / whole_portfolio_value * D("100")
    outside_scope_holdings = [
        item for item in holdings if item.strategy_scope == "outside_scope"
    ]
    allocation_corridor = portfolio.get("rebalancing", {}).get("corridor_pp", 1)
    allocation_on_target = (
        allocation_counts["underweight"] == 0
        and allocation_counts["overweight"] == 0
    )

    policy_status = (
        "non_compliant"
        if policy_errors
        else ("attention" if policy_warnings or policy_opportunities else "compliant")
    )

    return {
        "schema_version": 8,
        "portfolio_id": portfolio["portfolio"]["id"],
        # Do not expose the absolute Home Assistant configuration path.
        "source_file": source_label,
        "summary": {
            "current_portfolio_value_eur": whole_portfolio_value,
            "whole_portfolio_value_eur": whole_portfolio_value,
            "whole_portfolio_position_count": len(holdings),
            "current_plan_value_eur": current_plan_value,
            "current_plan_whole_portfolio_pct": current_plan_whole_pct,
            "current_plan_position_count": len(recommendations),
            "current_plan_held_position_count": sum(
                1 for item in recommendations if item.current_value_eur > 0
            ),
            "outside_scope_value_eur": outside_scope_value,
            "outside_scope_whole_portfolio_pct": outside_scope_whole_pct,
            "outside_scope_position_count": len(outside_scope_holdings),
            # Kept for entity-ID and dashboard compatibility. From v1.2 onward
            # this value is the contribution allocated for one execution.
            "monthly_contribution_eur": contribution_per_execution,
            "contribution_per_execution_eur": contribution_per_execution,
            "plan_budget_amount_eur": plan_runtime.budget_amount_eur,
            "plan_budget_basis": plan_runtime.budget_basis,
            "plan_frequency": plan_runtime.frequency,
            "scheduled_executions_per_period": plan_runtime.executions_per_period,
            "plan_configuration_source": plan_runtime.configuration_source,
            "plan_name": plan_runtime.name,
            "recommended_total_eur": recommended_total,
            "unallocated_contribution_eur": unallocated_contribution,
            "purchase_count": purchase_count,
            "monthly_plan_ready": (
                (purchase_count > 0 or actionable_deferred)
                if execution_enabled
                else abs(unallocated_contribution) <= D("0.01")
            ),
            "available_investment_reserve_eur": investment_reserve,
            "remaining_investment_reserve_eur": remaining_reserve,
            "investment_reserve_source": (
                "gateway_balance"
                if reserve_available
                else ("unavailable" if reserve_required_but_unavailable else "contribution")
            ),
            "investment_reserve_as_of": source_metadata.get("investment_reserve_as_of"),
            **(
                {
                    "investment_account_balance_eur": source_metadata["investment_account_balance_eur"],
                    "eligible_investment_cash_eur": source_metadata["eligible_investment_cash_eur"],
                    "authorized_investment_cash_eur": source_metadata["authorized_investment_cash_eur"],
                    "investment_cash_authorization_policy": source_metadata["investment_cash_authorization_policy"],
                    "investment_cash_authorization_cap_eur": source_metadata["investment_cash_authorization_cap_eur"],
                    **(
                        {"investment_cash_authorization_retain_eur": source_metadata["investment_cash_authorization_retain_eur"]}
                        if "investment_cash_authorization_retain_eur" in source_metadata
                        else {}
                    ),
                }
                if cash_authorization_present
                else {}
            ),
            **(
                {
                    "provider_investment_cash": [
                        {
                            "provider_id": item.provider_id,
                            "provider_name": item.provider_name,
                            "available_eur": item.available_eur,
                            "remaining_eur": max(
                                D("0"), provider_remaining[item.provider_id]
                            ),
                            "as_of": item.as_of,
                            "account_balance_eur": item.account_balance_eur,
                            "eligible_eur": item.eligible_eur,
                            "authorized_eur": item.authorized_eur,
                            "authorization_policy": item.authorization_policy,
                            "authorization_cap_eur": item.authorization_cap_eur,
                            "authorization_retain_eur": item.authorization_retain_eur,
                        }
                        for item in provider_cash
                    ],
                    "provider_investment_cash_source_count": len(provider_cash),
                    "funding_transfers": [
                        transfer_plans[edge] for edge in sorted(transfer_plans)
                    ],
                    "estimated_funding_transfer_fees_eur": estimated_funding_transfer_fees,
                    "estimated_total_execution_costs_eur": (
                        estimated_transaction_fees + estimated_funding_transfer_fees
                    ),
                    "funding_transfer_count": funding_transfer_count,
                }
                if provider_cash
                else {}
            ),
            "execution_policy": (
                str(execution_config.get("policy", "monthly_continuity"))
                if isinstance(execution_config, dict) and execution_enabled
                else "legacy_distribution"
            ),
            "max_cost_ratio_pct": (
                D(str(execution_config.get("max_cost_ratio_pct", "1.50")))
                if isinstance(execution_config, dict) and execution_enabled
                else D("0")
            ),
            "max_orders_per_execution": (
                int(execution_config.get("max_orders_per_execution", 1))
                if isinstance(execution_config, dict) and execution_enabled
                else len(recommendations)
            ),
            "max_deferral_periods": (
                int(execution_config.get("max_deferral_periods", 3))
                if isinstance(execution_config, dict) and execution_enabled
                else 0
            ),
            "deferred_purchase_count": deferred_count,
            "deferred_contribution_eur": remaining_reserve if deferred_count else D("0"),
            "estimated_transaction_fees_eur": estimated_transaction_fees,
            "estimated_cash_outlay_eur": estimated_cash_outlay,
            "execution_state": execution_state,
            "additional_investment_cash_required_eur": additional_investment_cash_required,
            "payload_schema_version": 8,
            "engine_version": __version__,
            "source_provider": source_provider,
            "generated_at": timestamp.isoformat(),
            "source_count": int(source_metadata.get("source_count", 1)),
            "source_providers": list(source_metadata.get("source_providers", [source_provider])),
            "provider_count": int(source_metadata.get("provider_count", 1)),
            "provider_ids": list(source_metadata.get("provider_ids", [source_provider])),
            "source_summaries": list(source_metadata.get("source_summaries", [])),
            "source_conflict_count": int(source_metadata.get("source_conflict_count", 0)),
            "source_conflicts": list(source_metadata.get("source_conflicts", [])),
            "oldest_source_generated_at": source_metadata.get("oldest_source_generated_at", timestamp.isoformat()),
            "newest_source_generated_at": source_metadata.get("newest_source_generated_at", timestamp.isoformat()),
            "allocation_corridor_pp": allocation_corridor,
            "portfolio_allocation_on_target": allocation_on_target,
            "underweight_positions": allocation_counts["underweight"],
            "on_target_positions": allocation_counts["on_target"],
            "overweight_positions": allocation_counts["overweight"],
            "policy_status": policy_status,
            "failed_findings": len(failed),
            "accepted_exceptions": len(accepted),
            "policy_checks_evaluated": len(findings),
            "policy_error_findings": len(policy_errors),
            "policy_warning_findings": len(policy_warnings),
            "policy_opportunity_findings": len(policy_opportunities),
            "policy_accepted_exceptions": len(accepted),
            "policy_exception_reviews_required": len(exception_reviews_required),
            "mandatory_controls_compliant": not policy_errors and not policy_warnings,
            "next_exception_review_on": next_exception_review_on,
            "exception_review_overdue": bool(overdue_review_dates),
            "overdue_exception_reviews": len(overdue_review_dates),
            "oldest_overdue_exception_review_on": oldest_overdue_exception_review_on,
            "last_exception_decision_on": last_exception_decision_on,
            **coverage.to_dict(),
        },
        "holdings": [item.to_dict() for item in holdings],
        "recommendations": [item.to_dict() for item in recommendations],
        "policy_findings": [item.to_dict() for item in findings],
    }


def _file_timestamp(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _normalise_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _load_optional_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exceptions": []}
    return load_yaml(path)


def _outside_scope_id(identifier: str, used: set[str]) -> str:
    token = _POSITION_ID_RE.sub("_", identifier.casefold()).strip("_")
    if not token:
        raise ValueError("Could not derive a stable position ID from identifier")
    candidate = f"holding_{token}"
    if candidate not in used:
        used.add(candidate)
        return candidate
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:8]
    candidate = f"holding_{token}_{digest}"
    if candidate in used:
        raise ValueError("Could not derive a unique stable position ID")
    used.add(candidate)
    return candidate


def _build_holdings(positions, plan_document, recommendations):
    funds = target_funds(plan_document)
    identity_index = build_position_identity_index(positions.values())
    targets_by_position: dict[int, dict[str, Any]] = {}
    for fund in funds:
        matched = match_position_for_target(fund, identity_index)
        if matched is None:
            continue
        marker = id(matched)
        if marker in targets_by_position:
            raise ValueError("One portfolio position matches multiple configured targets")
        targets_by_position[marker] = fund
    recommendation_by_wkn = {item.wkn: item for item in recommendations}
    total = sum(position.value_eur for position in positions.values())
    if total <= 0:
        raise ValueError("Whole portfolio value must be positive")

    holdings: list[Holding] = []
    used_position_ids = {str(item["id"]) for item in funds}
    for source_key in sorted(positions):
        position = positions[source_key]
        target = targets_by_position.get(id(position))
        recommendation = (
            recommendation_by_wkn.get(target["wkn"]) if target is not None else None
        )
        in_plan = target is not None
        position_isin = normalized_isin(position.isin)
        position_wkn = normalized_wkn(position.wkn, isin=position.isin)
        outside_identity = position_isin or position_wkn or str(source_key)
        holdings.append(
            Holding(
                position_id=(
                    target["id"]
                    if target
                    else _outside_scope_id(outside_identity, used_position_ids)
                ),
                wkn=target["wkn"] if target else position_wkn,
                isin=target["isin"] if target else position_isin,
                name=target["name"] if target else position.name,
                instrument_type=position.instrument_type,
                source_type=position.source_type,
                current_value_eur=position.value_eur,
                quantity=position.quantity,
                whole_portfolio_pct=position.value_eur / total * D("100"),
                strategy_scope="current_plan" if in_plan else "outside_scope",
                plan_fund_id=target["id"] if target else None,
                plan_current_pct=(
                    recommendation.current_pct if recommendation else None
                ),
                source_ids=position.source_ids,
                source_values_eur=position.source_values_eur,
            )
        )
    return holdings
