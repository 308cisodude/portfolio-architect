from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SENSOR = ROOT / "custom_components" / "portfolio_architect" / "sensor.py"
DASHBOARD = ROOT / "dashboard" / "bilingual-dashboard.yaml"
TRANSLATIONS = ROOT / "custom_components" / "portfolio_architect" / "translations"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_bounded_explanation_entities_exist() -> None:
    source = SENSOR.read_text(encoding="utf-8")
    for class_name in (
        "PortfolioAllocationExplanationSensor",
        "PortfolioPurchaseExplanationSensor",
        "PortfolioPolicyDecisionDetailSensor",
    ):
        assert f"class {class_name}" in source
    assert '"allocation_explanation"' in source
    assert '"purchase_explanation"' in source
    assert 'policy_decision' in source
    assert '"reason_code"' in source


def test_dashboard_routes_native_interactions_to_bounded_details() -> None:
    data = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    cards = list(_walk(data))

    drift_cards = [c for c in cards if str(c.get("entity", "")).endswith("_allocation_drift")]
    assert drift_cards
    for card in drift_cards:
        entity = card["entity"]
        assert card["tap_action"] == {
            "action": "more-info",
            "entity": entity.removesuffix("_allocation_drift") + "_allocation_explanation",
        }

    purchase_cards = [c for c in cards if c.get("type") == "tile" and str(c.get("entity", "")).endswith("_proposed_buy")]
    assert purchase_cards
    for card in purchase_cards:
        entity = card["entity"]
        assert card["tap_action"] == {
            "action": "more-info",
            "entity": entity.removesuffix("_proposed_buy") + "_isin",
        }
        assert card["hold_action"] == {
            "action": "more-info",
            "entity": entity.removesuffix("_proposed_buy") + "_purchase_explanation",
        }

    policy_cards = [c for c in cards if c.get("type") == "tile" and str(c.get("entity", "")).endswith("_policy_finding")]
    assert policy_cards
    for card in policy_cards:
        entity = card["entity"]
        assert card["tap_action"] == {
            "action": "more-info",
            "entity": entity.removesuffix("_policy_finding") + "_policy_decision",
        }


def test_explanation_translations_are_bilingual_and_bounded() -> None:
    required = {"allocation_explanation", "purchase_explanation", "policy_decision_detail"}
    for language in ("en", "de"):
        data = json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
        sensors = data["entity"]["sensor"]
        assert required <= sensors.keys()
        for key in required:
            attributes = sensors[key].get("state_attributes", {})
            assert "message" not in attributes
            assert "exception_rationale" not in attributes
            assert "source_values_eur" not in attributes
