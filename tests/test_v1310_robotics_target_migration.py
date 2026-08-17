"""v1.31.0 canonical Robotics-target and superseded-exception contracts."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.calculator import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.execution import ExecutionConfig, preferred_execution_route  # noqa: E402
from engine.importers import CsvSourceConfig, PROVIDER_COMDIRECT, read_positions  # noqa: E402
from engine.policy import evaluate  # noqa: E402

D = Decimal
CONFIG = ROOT / "examples" / "current-plan"
OLD_ROBOTICS_ISIN = "IE00BYWZ0333"
NEW_ROBOTICS_ISIN = "IE00BYZK4552"


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


def test_robotics_target_is_now_the_accumulating_share_class() -> None:
    portfolio = _load("portfolio.yaml")
    robotics = next(item for item in portfolio["portfolio"]["allocation"] if item["id"] == "robotics")
    assert robotics == {
        "id": "robotics",
        "name": "iShares Automation & Robotics UCITS ETF USD Acc",
        "wkn": "A2ANH0",
        "isin": NEW_ROBOTICS_ISIN,
        "target_pct": 5,
        "buy_enabled": True,
    }
    assert all(item["isin"] != OLD_ROBOTICS_ISIN for item in portfolio["portfolio"]["allocation"])

    instruments = _load("instruments.yaml")["instruments"]
    assert instruments[NEW_ROBOTICS_ISIN]["distribution"] == "accumulating"
    assert instruments[NEW_ROBOTICS_ISIN]["ucits"] is True
    # Retaining metadata for the legacy holding must not place it back in plan scope.
    assert instruments[OLD_ROBOTICS_ISIN]["distribution"] == "distributing"


def test_reference_broker_has_only_the_verified_tr_robotics_savings_plan_route() -> None:
    broker = _load("broker.yaml")
    assert broker["schema_version"] == 2
    tr = broker["providers"]["trade_republic"]
    assert tr["as_of"] == "2026-08-17"
    assert "manual_order" not in tr
    assert set(tr["savings_plans"]) == {NEW_ROBOTICS_ISIN}
    assert tr["savings_plans"][NEW_ROBOTICS_ISIN]["available"] is True
    assert tr["savings_plans"][NEW_ROBOTICS_ISIN]["fee_pct"] == 0

    route = preferred_execution_route(
        isin=NEW_ROBOTICS_ISIN,
        reference_amount_eur=D("350"),
        broker=broker,
        config=ExecutionConfig(enabled=True),
        evaluated_on=date(2026, 8, 17),
    )
    assert route.provider_id == "trade_republic"
    assert route.provider_name == "Trade Republic"
    assert route.route == "free_savings_plan"
    assert route.fee_eur == D("0.00")
    assert route.fee_data_as_of == "2026-08-17"


def test_old_distributing_holding_becomes_outside_scope_without_sell_semantics() -> None:
    positions = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv",
        CsvSourceConfig(provider=PROVIDER_COMDIRECT),
    )
    payload = calculate_portfolio_payload_from_positions(
        positions,
        CONFIG,
        evaluated_at=datetime(2026, 8, 17, 13, 0, tzinfo=timezone.utc),
        source_provider=PROVIDER_COMDIRECT,
        source_label="Comdirect CSV",
    )

    summary = payload["summary"]
    assert summary["target_positions_total"] == 7
    assert summary["target_positions_held"] == 6
    assert summary["target_positions_missing"] == 1
    assert summary["target_architecture_complete"] is False
    assert summary["missing_target_fund_ids"] == ["robotics"]
    assert summary["policy_accepted_exceptions"] == 0
    assert summary["policy_exception_reviews_required"] == 0

    robotics = next(item for item in payload["recommendations"] if item["fund_id"] == "robotics")
    assert robotics["isin"] == NEW_ROBOTICS_ISIN
    assert robotics["wkn"] == "A2ANH0"
    assert robotics["current_value_eur"] == D("0")
    assert robotics["buy_enabled"] is True
    assert robotics["proposed_buy_eur"] > 0

    old = next(item for item in payload["holdings"] if item["isin"] == OLD_ROBOTICS_ISIN)
    assert old["position_id"] == "holding_ie00bywz0333"
    assert old["strategy_scope"] == "outside_scope"
    assert old["plan_fund_id"] is None
    assert old["current_value_eur"] == D("500.00")
    assert all(item["isin"] != OLD_ROBOTICS_ISIN for item in payload["recommendations"])


def test_superseded_robotics_exception_is_valid_history_but_not_active_policy() -> None:
    exceptions = _load("exceptions.yaml")
    item = exceptions["exceptions"][0]
    assert item["status"] == "superseded"
    assert item["instrument_id"] == OLD_ROBOTICS_ISIN
    assert item["approved_on"] == date(2026, 7, 27)
    assert item["last_reviewed_on"] == "2026-08-17"
    assert item["review_on"] is None
    assert item["superseded_on"] == "2026-08-17"
    assert item["superseded_by_instrument_id"] == NEW_ROBOTICS_ISIN
    assert item["superseded_reason"] == "preferred_accumulating_route_available"

    findings = evaluate(
        _load("portfolio.yaml"),
        _load("policy.yaml"),
        _load("instruments.yaml"),
        _load("broker.yaml"),
        exceptions,
        evaluated_on=date(2026, 8, 17),
        preferred_execution_providers={NEW_ROBOTICS_ISIN: "trade_republic"},
    )
    assert not any(item.status in {"accepted_exception", "review_required"} for item in findings)
    accumulating = next(
        item
        for item in findings
        if item.instrument_id == NEW_ROBOTICS_ISIN and item.rule == "accumulating_preferred"
    )
    assert accumulating.status == "pass"


def test_superseded_exception_audit_fields_fail_closed() -> None:
    base = _load("exceptions.yaml")
    broken = yaml.safe_load(yaml.safe_dump(base))
    broken["exceptions"][0]["superseded_on"] = "2026-08-18"
    with pytest.raises(ValueError, match="future"):
        evaluate(
            _load("portfolio.yaml"), _load("policy.yaml"), _load("instruments.yaml"),
            _load("broker.yaml"), broken, evaluated_on=date(2026, 8, 17)
        )

    broken = yaml.safe_load(yaml.safe_dump(base))
    broken["exceptions"][0]["superseded_by_instrument_id"] = OLD_ROBOTICS_ISIN
    with pytest.raises(ValueError, match="replacement instrument"):
        evaluate(
            _load("portfolio.yaml"), _load("policy.yaml"), _load("instruments.yaml"),
            _load("broker.yaml"), broken, evaluated_on=date(2026, 8, 17)
        )


def test_reference_dashboard_surfaces_legacy_robotics_as_outside_scope() -> None:
    distribution_files = (
        ROOT / "dashboard" / "allocation-stack.yaml",
        ROOT / "dashboard" / "en" / "allocation-stack.yaml",
        ROOT / "dashboard" / "de" / "allocation-stack.yaml",
        ROOT / "dashboard" / ".tmp_en.yaml",
        ROOT / "dashboard" / ".tmp_de.yaml",
        ROOT / "dashboard" / "en" / "view.yaml",
        ROOT / "dashboard" / "de" / "view.yaml",
        ROOT / "dashboard" / "bilingual-dashboard.yaml",
    )
    for path in distribution_files:
        text = path.read_text(encoding="utf-8")
        assert "sensor.portfolio_architect_robotics_whole_portfolio_allocation" in text, path
        assert "sensor.portfolio_architect_holding_ie00bywz0333_whole_portfolio_allocation" in text, path

    for relative in (".tmp_en.yaml", ".tmp_de.yaml", "en/view.yaml", "de/view.yaml"):
        text = (ROOT / "dashboard" / relative).read_text(encoding="utf-8")
        assert "sensor.portfolio_architect_holding_ie00bywz0333_holding_value" in text
    bilingual = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")
    assert bilingual.count("sensor.portfolio_architect_holding_ie00bywz0333_holding_value") == 4
