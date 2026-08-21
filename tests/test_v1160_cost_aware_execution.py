"""v1.16.0 route-aware transaction-cost and reserve contracts."""

from decimal import Decimal
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.execution import (  # noqa: E402
    ExecutionConfig,
    efficient_manual_order_minimum,
    estimate_manual_order,
)
from engine.models import Position  # noqa: E402
from engine.rebalance import allocate_buys  # noqa: E402

D = Decimal


def _document() -> dict:
    return {
        "portfolio": {
            "monthly_contribution": 350,
            "allocation": [
                {
                    "id": "underweight",
                    "name": "Underweight ETF",
                    "wkn": "AAAAAA",
                    "isin": "IE0000000001",
                    "target_pct": 80,
                    "buy_enabled": True,
                },
                {
                    "id": "overweight",
                    "name": "Overweight ETF",
                    "wkn": "BBBBBB",
                    "isin": "IE0000000002",
                    "target_pct": 20,
                    "buy_enabled": True,
                },
            ],
        },
        "rebalancing": {
            "corridor_pp": 1,
            "minimum_trade": 20,
            "rounding_step": 10,
        },
    }


def _positions() -> dict[str, Position]:
    return {
        "AAAAAA": Position(
            wkn="AAAAAA",
            isin="IE0000000001",
            name="Underweight ETF",
            instrument_type="etf",
            source_type="test",
            value_eur=D("1000"),
        ),
        "BBBBBB": Position(
            wkn="BBBBBB",
            isin="IE0000000002",
            name="Overweight ETF",
            instrument_type="etf",
            source_type="test",
            value_eur=D("9000"),
        ),
    }


def _execution(**overrides) -> dict:
    result = {
        "enabled": True,
        "policy": "balanced",
        "max_cost_ratio_pct": 1.5,
        "max_deferral_periods": 3,
        "max_orders_per_execution": 1,
        "reserve_mode": "gateway_balance",
    }
    result.update(overrides)
    return result


def _broker(*, fee_pct: Decimal | None) -> dict:
    plans = {}
    if fee_pct is not None:
        plans["IE0000000001"] = {"available": True, "fee_pct": fee_pct}
    return {"broker": {"savings_plans": plans}}


def _underweight(result):
    return next(item for item in result if item.fund_id == "underweight")


def test_comdirect_statement_fee_profile_matches_observed_order() -> None:
    estimate = estimate_manual_order(D("124.78"), ExecutionConfig(enabled=True))
    assert estimate.fee_eur == D("15.30")
    assert estimate.cost_ratio_pct == D("12.261580")
    assert efficient_manual_order_minimum(
        ExecutionConfig(enabled=True, max_cost_ratio_pct=D("1.50"))
    ) == D("1020.00")


def test_paid_savings_plan_preserves_monthly_continuity_at_accepted_ratio() -> None:
    result = allocate_buys(
        _positions(),
        _document(),
        broker=_broker(fee_pct=D("1.5")),
        execution=_execution(),
        available_reserve_eur=D("350"),
    )
    item = _underweight(result)
    assert item.proposed_buy_eur == D("344.83")
    assert item.execution_route == "paid_savings_plan"
    assert item.estimated_fee_eur == D("5.17")
    assert item.estimated_cash_outlay_eur == D("350.00")
    assert item.estimated_cost_ratio_pct == D("1.500000")
    assert item.deferred is False



def test_paid_savings_plan_never_overdraws_the_live_reserve() -> None:
    result = allocate_buys(
        _positions(),
        _document(),
        broker=_broker(fee_pct=D("1.5")),
        execution=_execution(),
        available_reserve_eur=D("349"),
    )
    item = _underweight(result)
    assert item.proposed_buy_eur == D("343.84")
    assert item.estimated_fee_eur == D("5.16")
    assert item.estimated_cash_outlay_eur == D("349.00")


def test_free_savings_plan_is_never_deferred_for_transaction_costs() -> None:
    result = allocate_buys(
        _positions(),
        _document(),
        broker=_broker(fee_pct=D("0")),
        execution=_execution(max_cost_ratio_pct=0),
        available_reserve_eur=D("350"),
    )
    item = _underweight(result)
    assert item.proposed_buy_eur == D("350.00")
    assert item.execution_route == "free_savings_plan"
    assert item.estimated_fee_eur == D("0.00")
    assert item.deferred is False


def test_manual_order_is_deferred_until_fixed_cost_ratio_is_efficient() -> None:
    result = allocate_buys(
        _positions(),
        _document(),
        broker=_broker(fee_pct=None),
        execution=_execution(),
        available_reserve_eur=D("350"),
    )
    item = _underweight(result)
    assert item.proposed_buy_eur == D("0")
    assert item.execution_route == "manual_order"
    assert item.estimated_fee_eur == D("15.30")
    assert item.estimated_cash_outlay_eur == D("345.30")
    assert item.estimated_cost_ratio_pct == D("4.636364")
    assert item.additional_reserve_required_eur == D("685.30")
    assert item.recommendation_reason == "transaction_cost_threshold_not_met"
    assert item.deferred is True


def test_accumulated_manual_order_becomes_eligible_at_cost_ceiling() -> None:
    result = allocate_buys(
        _positions(),
        _document(),
        broker=_broker(fee_pct=None),
        execution=_execution(),
        available_reserve_eur=D("1050"),
    )
    item = _underweight(result)
    assert item.proposed_buy_eur == D("1030.00")
    assert item.execution_route == "manual_order"
    assert item.estimated_fee_eur == D("15.30")
    assert item.estimated_cash_outlay_eur == D("1045.30")
    assert item.estimated_cost_ratio_pct == D("1.485437")
    assert item.deferred is False


def test_balanced_policy_forces_one_order_after_configured_deferral_limit() -> None:
    result = allocate_buys(
        _positions(),
        _document(),
        broker=_broker(fee_pct=None),
        execution=_execution(max_deferral_periods=1),
        available_reserve_eur=D("700"),
    )
    item = _underweight(result)
    assert item.proposed_buy_eur == D("680.00")
    assert item.estimated_cash_outlay_eur == D("695.30")
    assert item.estimated_cost_ratio_pct == D("2.250000")
    assert item.recommendation_reason == "maximum_deferral_reached"


def test_gateway_balance_mode_fails_closed_when_reserve_is_unavailable() -> None:
    result = allocate_buys(
        _positions(),
        _document(),
        broker=_broker(fee_pct=D("1.5")),
        execution=_execution(),
        available_reserve_eur=None,
    )
    item = _underweight(result)
    assert item.proposed_buy_eur == D("0")
    assert item.execution_route == "unavailable"
    assert item.recommendation_reason == "investment_reserve_unavailable"
    assert item.deferred is True


def test_multiple_cost_aware_orders_never_exceed_available_reserve() -> None:
    broker = {
        "broker": {
            "savings_plans": {
                "IE0000000001": {"available": True, "fee_pct": 0},
                "IE0000000002": {"available": True, "fee_pct": 0},
            }
        }
    }
    result = allocate_buys(
        _positions(),
        _document(),
        broker=broker,
        execution=_execution(max_orders_per_execution=2),
        available_reserve_eur=D("350"),
    )
    assert sum(item.estimated_cash_outlay_eur for item in result if item.proposed_buy_eur > 0) <= D("350")
    assert sum(1 for item in result if item.proposed_buy_eur > 0) <= 2


def test_v1160_dashboard_keeps_native_cost_aware_interaction_contract() -> None:
    dashboard = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text()

    assert dashboard.count("type: markdown") == 2
    assert "sensor.portfolio_architect_execution_path" in dashboard
    assert "custom:" not in dashboard
    for entity in (
        "sensor.portfolio_architect_execution_policy",
        "sensor.portfolio_architect_available_investment_reserve",
        "sensor.portfolio_architect_estimated_transaction_fees",
        "sensor.portfolio_architect_deferred_purchase_count",
    ):
        assert dashboard.count(entity) >= 2

    # v1.36 replaced instrument-specific purchase tiles with bounded generic aliases.
    # v1.38 keeps that inventory dynamic while restoring copy-friendly ISIN access:
    # tap opens the same slot's ISIN entity and hold keeps purchase explanation.
    assert dashboard.count("type: entity-filter") >= 2
    assert "sensor.portfolio_architect_presentation_target_01_proposed_buy" in dashboard
    assert "sensor.portfolio_architect_presentation_target_32_proposed_buy" in dashboard
    assert "sensor.portfolio_architect_presentation_target_01_purchase_explanation" in dashboard
    assert "sensor.portfolio_architect_presentation_target_32_purchase_explanation" in dashboard
    assert "sensor.portfolio_architect_presentation_target_01_instrument_isin" in dashboard
    assert "sensor.portfolio_architect_presentation_target_32_instrument_isin" in dashboard


def test_v1160_gateway_public_snapshot_does_not_publish_account_identity() -> None:
    public_model_source = (
        ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "models.py"
    ).read_text()
    app_source = (
        ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "app.py"
    ).read_text()

    assert '"investment_reserve"' in public_model_source
    assert '"available_eur"' in public_model_source
    assert '"as_of"' in public_model_source
    reserve_block = public_model_source.split('data["investment_reserve"] = {', 1)[1].split('}', 1)[0]
    assert "account_id" not in reserve_block
    assert "iban" not in reserve_block.lower()
    assert '"account_id"' not in app_source
    assert '"iban"' not in app_source.lower()
