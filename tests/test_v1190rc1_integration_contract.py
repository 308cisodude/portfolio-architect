from __future__ import annotations

from datetime import date
from pathlib import Path
import json
import sys

import yaml

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "portfolio_architect"))
from engine.policy import evaluate  # noqa: E402


def _docs():
    portfolio = yaml.safe_load((ROOT / "examples/current-plan/portfolio.yaml").read_text())
    policy = yaml.safe_load((ROOT / "examples/current-plan/policy.yaml").read_text())
    instruments = yaml.safe_load((ROOT / "examples/current-plan/instruments.yaml").read_text())
    broker = yaml.safe_load((ROOT / "examples/current-plan/broker.yaml").read_text())
    return portfolio, policy, instruments, broker

def test_fee_verification_lifecycle_is_opt_in_bounded_and_current() -> None:
    portfolio, policy, instruments, broker = _docs()
    findings = evaluate(portfolio, policy, instruments, broker, evaluated_on=date(2026, 8, 4))
    fee = [item for item in findings if item.rule == "savings_plan_fee_verified_recently"]
    assert len(fee) == 7
    assert {item.status for item in fee} == {"pass"}
    broker["broker"]["savings_plans"]["IE00BJ0KDQ92"].pop("fee_verified_at")
    findings = evaluate(portfolio, policy, instruments, broker, evaluated_on=date(2026, 8, 4))
    world = next(item for item in findings if item.rule == "savings_plan_fee_verified_recently" and item.instrument_id == "IE00BJ0KDQ92")
    assert world.status == "fail"
    assert world.severity == "info"
    assert world.observed == "missing"
    assert world.expected == "within_90_days"

def test_copyable_order_identifier_block_is_bilingual_and_native() -> None:
    for language, title in (("en", "Order identifiers"), ("de", "Orderkennungen")):
        text = (ROOT / "dashboard" / language / "monthly-investment-plan.yaml").read_text()
        assert f"title: {title}" in text
        assert "type: markdown" in text
        assert "item.proposed_buy_eur | float > 0" in text
        assert "`{{ item.isin }}`" in text
        assert "sensor.portfolio_architect_purchase_count" in text

def test_release_is_prerelease_aware_and_gateway_is_experimental() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text()
    verifier = (ROOT / "tools/verify_release.py").read_text()
    app = yaml.safe_load((ROOT / "home_assistant_app/portfolio_architect_gateway/config.yaml").read_text())
    assert "--prerelease" in workflow
    assert '${GITHUB_REF_NAME#v}' in workflow
    assert r"(?:-(?:rc|beta|alpha)\d+)?" in verifier
    assert app["version"] == "1.19.0-rc1"
    assert app["stage"] == "experimental"

def test_probe_capability_is_absent_from_public_gateway_schema() -> None:
    server = (ROOT / "gateway/src/portfolio_architect_gateway/server.py").read_text().casefold()
    assert "fundflags" not in server
    assert "costindication" not in server
    assert "probe-result" not in server
