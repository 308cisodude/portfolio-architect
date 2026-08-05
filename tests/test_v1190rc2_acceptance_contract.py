from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "portfolio_architect"))
from engine.policy import evaluate  # noqa: E402

FUNDS = (
    "world",
    "emerging_markets",
    "world_small_cap",
    "healthcare",
    "ai_big_data",
    "cybersecurity",
    "robotics",
)


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


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


def test_recommended_buy_actions_are_copy_first_and_explanation_on_hold() -> None:
    for path in (
        ROOT / "dashboard/en/monthly-investment-plan.yaml",
        ROOT / "dashboard/de/monthly-investment-plan.yaml",
        ROOT / "dashboard/bilingual-dashboard.yaml",
    ):
        data = yaml.safe_load(path.read_text())
        cards = [
            item for item in _walk(data)
            if item.get("type") == "tile" and str(item.get("entity", "")).endswith("_proposed_buy")
        ]
        assert cards
        for card in cards:
            base = card["entity"].removesuffix("_proposed_buy")
            assert card["tap_action"] == {"action": "more-info", "entity": f"{base}_isin"}
            assert card["hold_action"] == {"action": "more-info", "entity": f"{base}_purchase_explanation"}


def test_order_identifier_block_uses_live_proposed_buy_entities() -> None:
    for language, title in (("en", "Order identifiers"), ("de", "Orderkennungen")):
        data = yaml.safe_load((ROOT / "dashboard" / language / "monthly-investment-plan.yaml").read_text())
        card = next(item for item in _walk(data) if item.get("type") == "markdown" and item.get("title") == title)
        text = card["content"]
        assert "state_attr('sensor.portfolio_architect', 'recommendations')" not in text
        assert "states(entity_id) | float(0) > 0" in text
        assert "state_attr(entity_id, 'fund_name')" in text
        assert "state_attr(entity_id, 'isin')" in text
        expected = {"sensor.portfolio_architect_purchase_count"}
        expected.update(f"sensor.portfolio_architect_{fund}_proposed_buy" for fund in FUNDS)
        assert set(card["entity_id"]) == expected


def test_release_is_prerelease_aware_and_gateway_is_experimental() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text()
    verifier = (ROOT / "tools/verify_release.py").read_text()
    app = yaml.safe_load((ROOT / "home_assistant_app/portfolio_architect_gateway/config.yaml").read_text())
    assert "--prerelease" in workflow
    assert '${GITHUB_REF_NAME#v}' in workflow
    assert r"(?:-(?:rc|beta|alpha)\d+)?" in verifier
    assert app["version"] == "1.19.0-rc2"
    assert app["stage"] == "experimental"


def test_acceptance_framing_rejects_savings_plan_promotion_inference() -> None:
    app = (ROOT / "gateway/src/portfolio_architect_gateway/app.py").read_text()
    notes = (ROOT / "docs/RELEASE-NOTES.md").read_text()
    probe = (ROOT / "docs/COMDIRECT-FEE-PROBE.md").read_text()
    assert "Read instrument metadata and venues" in app
    assert "not a promotion detector" in app
    for text in (notes, probe):
        assert "IE00BYWZ0333" in text
        assert "IE00BJ0KDQ92" in text
        assert "15.30" in text
        assert "not a savings-plan quotation" in text
    assert "no PhotoTAN" in notes
    assert "pending or open order" in notes


def test_probe_capability_is_absent_from_public_gateway_schema() -> None:
    server = (ROOT / "gateway/src/portfolio_architect_gateway/server.py").read_text().casefold()
    assert "fundflags" not in server
    assert "costindication" not in server
    assert "probe-result" not in server
