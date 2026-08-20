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


def _candidate_entity(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        entity = value.get("entity")
        return entity if isinstance(entity, str) else None
    return None


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


def test_dashboard_routes_dynamic_inventory_through_native_more_info() -> None:
    data = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    cards = list(_walk(data))

    dynamic_filters = [card for card in cards if card.get("type") == "entity-filter"]
    assert dynamic_filters
    assert any(any(_candidate_entity(item) == "sensor.portfolio_architect_presentation_target_01_proposed_buy" for item in card.get("entities", [])) for card in dynamic_filters)
    # v1.39.0 routes allocation drift through native Conditional + Tile cards
    # instead of the older entity-filter list, while keeping the same bounded
    # generic presentation-slot identity and native more-info explainability.
    drift_cards = [
        card
        for card in cards
        if card.get("type") == "conditional"
        and isinstance(card.get("card"), dict)
        and card["card"].get("entity")
        == "sensor.portfolio_architect_presentation_target_01_allocation_drift"
    ]
    assert len(drift_cards) == 6
    assert all(
        card["card"].get("tap_action")
        == {
            "action": "more-info",
            "entity": "sensor.portfolio_architect_presentation_target_01_allocation_explanation",
        }
        for card in drift_cards
    )
    assert any(any(_candidate_entity(item) == "sensor.portfolio_architect_presentation_policy_001_finding" for item in card.get("entities", [])) for card in dynamic_filters)
    assert all(card.get("card", {}).get("type") in {"entities", "glance"} for card in dynamic_filters if isinstance(card.get("card"), dict))

    sensor = (ROOT / "custom_components/portfolio_architect/sensor.py").read_text(encoding="utf-8")
    target_slot = sensor.split("class PortfolioTargetPresentationSlotSensor", 1)[1].split(
        "class PortfolioOutsidePresentationSlotSensor", 1
    )[0]
    policy_slot = sensor.split("class PortfolioPolicyPresentationSlotSensor", 1)[1]
    assert '"stable_identity"' in target_slot
    assert '"stable_identity"' in policy_slot


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
