"""v1.30.0 provider-aware execution-policy and exception-review contracts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.execution import (  # noqa: E402
    ExecutionConfig,
    choose_route_for_cash,
    execution_providers,
    preferred_execution_route,
    preferred_savings_plan_route,
)
from engine.policy import evaluate  # noqa: E402

D = Decimal
ROBOTICS_ISIN = "IE00BYWZ0333"


def _provider_broker(*, trade_republic_as_of: str = "2026-08-15") -> dict:
    return {
        "schema_version": 2,
        "fee_data_max_age_days": 30,
        "providers": {
            "comdirect": {
                "name": "Comdirect",
                "source": "synthetic-regression-fixture",
                "as_of": "2026-08-10",
                "priority": 20,
                "savings_plans": {
                    ROBOTICS_ISIN: {"available": True, "fee_pct": 1.5},
                },
                "manual_order": {
                    "available": True,
                    "commission_base_eur": 4.90,
                    "commission_pct": 0.25,
                    "commission_min_eur": 9.90,
                    "commission_max_eur": 59.90,
                    "venue_fee_pct": 0.0025,
                    "venue_fee_min_eur": 2.50,
                    "settlement_fee_eur": 2.90,
                },
            },
            "trade_republic": {
                "name": "Trade Republic",
                "source": "synthetic-regression-fixture",
                "as_of": trade_republic_as_of,
                "priority": 10,
                "savings_plans": {
                    ROBOTICS_ISIN: {"available": True, "fee_pct": 0},
                },
                "manual_order": {
                    "available": True,
                    "commission_base_eur": 1,
                    "commission_pct": 0,
                    "commission_min_eur": 1,
                    "commission_max_eur": 1,
                    "venue_fee_pct": 0,
                    "venue_fee_min_eur": 0,
                    "settlement_fee_eur": 0,
                },
            },
        },
    }


def _portfolio() -> dict:
    return {
        "portfolio": {
            "allocation": [
                {
                    "id": "robotics",
                    "name": "Robotics ETF",
                    "isin": ROBOTICS_ISIN,
                    "wkn": "A2ANH1",
                    "target_pct": 100,
                    "buy_enabled": True,
                }
            ]
        }
    }


def _policy() -> dict:
    return {
        "policy": {
            "rules": {
                "ucits_required": True,
                "accumulating_preferred": True,
                "ireland_preferred": True,
                "max_ter_pct": 0.70,
                "minimum_fund_size_eur": 100_000_000,
                "savings_plan_required": True,
                "free_savings_plan_preferred": True,
            },
            "severities": {
                "ucits_required": "error",
                "accumulating_preferred": "warning",
                "ireland_preferred": "warning",
                "max_ter_pct": "warning",
                "minimum_fund_size_eur": "warning",
                "savings_plan_required": "error",
                "free_savings_plan_preferred": "info",
            },
        }
    }


def _instruments() -> dict:
    return {
        "instruments": {
            ROBOTICS_ISIN: {
                "ucits": True,
                "distribution": "distributing",
                "domicile": "IE",
                "ter_pct": 0.40,
                "fund_size_eur": 500_000_000,
            }
        }
    }


def _exception(expected_provider: str = "comdirect") -> dict:
    return {
        "schema_version": 2,
        "exceptions": [
            {
                "id": "robotics_distributing_share_class",
                "instrument_id": ROBOTICS_ISIN,
                "rule": "accumulating_preferred",
                "status": "accepted",
                "rationale": "Synthetic regression exception.",
                "approved_on": "2026-07-27",
                "last_reviewed_on": "2026-07-27",
                "review_on": "2027-07-27",
                "expires_on": None,
                "assumptions": {
                    "preferred_execution_provider": expected_provider,
                },
            }
        ],
    }


def test_schema2_prefers_fresh_zero_fee_provider() -> None:
    broker = _provider_broker()
    route = preferred_savings_plan_route(
        broker, ROBOTICS_ISIN, evaluated_on=date(2026, 8, 16)
    )
    assert route is not None
    assert route.provider_id == "trade_republic"
    assert route.provider_name == "Trade Republic"
    assert route.fee_pct == D("0.0000")

    chosen = choose_route_for_cash(
        isin=ROBOTICS_ISIN,
        desired_amount_eur=D("350"),
        periodic_cash_budget_eur=D("350"),
        reserve_cash_budget_eur=D("350"),
        minimum_order_eur=D("20"),
        rounding_step_eur=D("10"),
        broker=broker,
        config=ExecutionConfig(enabled=True, max_cost_ratio_pct=D("1.5")),
        evaluated_on=date(2026, 8, 16),
    )
    assert chosen.route == "free_savings_plan"
    assert chosen.provider_id == "trade_republic"
    assert chosen.provider_name == "Trade Republic"
    assert chosen.order_amount_eur == D("350.00")
    assert chosen.fee_eur == D("0.00")
    assert chosen.fee_data_as_of == "2026-08-15"


def test_stale_provider_is_known_but_ineligible() -> None:
    broker = _provider_broker(trade_republic_as_of="2026-06-01")
    providers = {item.provider_id: item for item in execution_providers(
        broker, evaluated_on=date(2026, 8, 16)
    )}
    assert providers["trade_republic"].fresh is False
    route = preferred_savings_plan_route(
        broker, ROBOTICS_ISIN, evaluated_on=date(2026, 8, 16)
    )
    assert route is not None
    assert route.provider_id == "comdirect"
    assert route.fee_pct == D("1.5000")


def test_schema2_rejects_future_fee_evidence() -> None:
    broker = _provider_broker(trade_republic_as_of="2026-08-17")
    with pytest.raises(ValueError, match="future"):
        execution_providers(broker, evaluated_on=date(2026, 8, 16))


def test_exception_assumption_becomes_review_required_when_provider_changes() -> None:
    findings = evaluate(
        _portfolio(),
        _policy(),
        _instruments(),
        _provider_broker(),
        _exception(),
        evaluated_on=date(2026, 8, 16),
        preferred_execution_providers={ROBOTICS_ISIN: "trade_republic"},
    )
    robotics = next(item for item in findings if item.rule == "accumulating_preferred")
    assert robotics.status == "review_required"
    assert robotics.severity == "warning"
    assert robotics.exception_id == "robotics_distributing_share_class"
    assert robotics.exception_review_reason == "preferred_execution_provider_changed"
    assert robotics.exception_expected_provider == "comdirect"
    assert robotics.exception_observed_provider == "trade_republic"

    fee_finding = next(item for item in findings if item.rule == "free_savings_plan_preferred")
    assert fee_finding.status == "pass"
    assert fee_finding.observed == 0.0


def test_exception_remains_accepted_while_provider_assumption_holds() -> None:
    findings = evaluate(
        _portfolio(),
        _policy(),
        _instruments(),
        _provider_broker(trade_republic_as_of="2026-06-01"),
        _exception(),
        evaluated_on=date(2026, 8, 16),
        preferred_execution_providers={ROBOTICS_ISIN: "comdirect"},
    )
    robotics = next(item for item in findings if item.rule == "accumulating_preferred")
    assert robotics.status == "accepted_exception"
    assert robotics.exception_review_reason is None


def test_preferred_execution_route_uses_provider_not_acquisition_source() -> None:
    route = preferred_execution_route(
        isin=ROBOTICS_ISIN,
        reference_amount_eur=D("350"),
        broker=_provider_broker(),
        config=ExecutionConfig(enabled=True),
        evaluated_on=date(2026, 8, 16),
    )
    assert route.provider_id == "trade_republic"
    assert route.route == "free_savings_plan"


def test_current_public_exception_retains_v130_provider_assumption_as_history() -> None:
    text = (ROOT / "examples/current-plan/exceptions.yaml").read_text(encoding="utf-8")
    assert "schema_version: 2" in text
    assert "preferred_execution_provider: comdirect" in text
    assert "status: superseded" in text
    assert "superseded_by_instrument_id: IE00BYZK4552" in text


def test_dashboard_purchase_aliases_preserve_execution_provider_for_native_more_info() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    slot = sensor.split("class PortfolioTargetPresentationSlotSensor", 1)[1].split(
        "class PortfolioOutsidePresentationSlotSensor", 1
    )[0]
    assert '"execution_provider_name"' in slot or "position.attributes" in slot
    assert '"stable_identity"' in slot

    for relative in (
        "dashboard/en/monthly-investment-plan.yaml",
        "dashboard/de/monthly-investment-plan.yaml",
        "dashboard/en/view.yaml",
        "dashboard/de/view.yaml",
        "dashboard/bilingual-dashboard.yaml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "presentation_target_01_proposed_buy" in text, relative
        assert "type: entity-filter" in text, relative
        assert "custom:" not in text, relative


def test_decision_trace_detects_execution_provider_change() -> None:
    module_path = COMPONENT / "decision_trace.py"
    spec = importlib.util.spec_from_file_location("pa_v1300_decision_trace", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    old = module.PositionDecisionSnapshot(
        fund_id="robotics",
        fund_name="Robotics ETF",
        allocation_status="underweight",
        deviation_pp=-2.0,
        proposed_buy_eur=350,
        execution_route="free_savings_plan",
        execution_state="ready",
        recommendation_reason="most_underweight_cost_efficient",
        deferred=False,
        execution_provider="comdirect",
    )
    new = module.PositionDecisionSnapshot(
        fund_id="robotics",
        fund_name="Robotics ETF",
        allocation_status="underweight",
        deviation_pp=-2.0,
        proposed_buy_eur=350,
        execution_route="free_savings_plan",
        execution_state="ready",
        recommendation_reason="most_underweight_cost_efficient",
        deferred=False,
        execution_provider="trade_republic",
    )
    change = module._position_change(old, new)
    assert change is not None
    assert "execution_provider_changed" in change["reason_codes"]
    assert change["previous_execution_provider"] == "comdirect"
    assert change["current_execution_provider"] == "trade_republic"

    legacy = old.to_dict()
    legacy.pop("execution_provider")
    assert module.PositionDecisionSnapshot.from_dict(legacy).execution_provider is None


def test_full_payload_reopens_route_scoped_exception_when_provider_changes(tmp_path: Path) -> None:
    import shutil
    from datetime import datetime, timezone
    import yaml

    from engine.calculator import calculate_portfolio_payload_from_positions
    from engine.importers import CsvSourceConfig, PROVIDER_COMDIRECT, read_positions

    config_dir = tmp_path / "plan"
    shutil.copytree(ROOT / "examples" / "current-plan", config_dir)
    current_broker = yaml.safe_load((config_dir / "broker.yaml").read_text(encoding="utf-8"))
    comdirect_plans = current_broker["providers"]["comdirect"]["savings_plans"]
    provider_broker = _provider_broker()
    provider_broker["providers"]["comdirect"]["savings_plans"] = comdirect_plans
    (config_dir / "broker.yaml").write_text(
        yaml.safe_dump(provider_broker, sort_keys=False), encoding="utf-8"
    )

    # Keep the v1.30 full-payload regression independent from the evolving current
    # reference plan: reconstruct the distributing target and accepted exception that
    # originally exercised provider-assumption review.
    portfolio = yaml.safe_load((config_dir / "portfolio.yaml").read_text(encoding="utf-8"))
    robotics = next(item for item in portfolio["portfolio"]["allocation"] if item["isin"] == "IE00BYZK4552")
    robotics.update(
        name="iShares Automation & Robotics UCITS ETF USD Dist",
        wkn="A2ANH1",
        isin=ROBOTICS_ISIN,
    )
    (config_dir / "portfolio.yaml").write_text(
        yaml.safe_dump(portfolio, sort_keys=False), encoding="utf-8"
    )
    (config_dir / "exceptions.yaml").write_text(
        yaml.safe_dump(_exception(), sort_keys=False), encoding="utf-8"
    )

    positions = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv",
        CsvSourceConfig(provider=PROVIDER_COMDIRECT),
    )
    payload = calculate_portfolio_payload_from_positions(
        positions,
        config_dir,
        evaluated_at=datetime(2026, 8, 16, 20, 0, tzinfo=timezone.utc),
        source_provider=PROVIDER_COMDIRECT,
        source_label="Comdirect CSV",
    )
    robotics = next(
        item
        for item in payload["policy_findings"]
        if item["instrument_id"] == ROBOTICS_ISIN
        and item["rule"] == "accumulating_preferred"
    )
    assert robotics["status"] == "review_required"
    assert robotics["exception_expected_provider"] == "comdirect"
    assert robotics["exception_observed_provider"] == "trade_republic"
    assert payload["summary"]["policy_accepted_exceptions"] == 0
    assert payload["summary"]["policy_exception_reviews_required"] == 1
    assert payload["summary"]["next_exception_review_on"] is None
    assert payload["summary"]["last_exception_decision_on"] == "2026-07-27"
