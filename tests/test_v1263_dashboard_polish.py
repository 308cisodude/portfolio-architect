from __future__ import annotations

from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))


CHECKS = "sensor.portfolio_architect_policy_checks_evaluated"
OPPORTUNITIES = "sensor.portfolio_architect_optimisation_opportunity_count"
EXCEPTIONS = "sensor.portfolio_architect_accepted_exception_count"
_PLAN = yaml.safe_load((ROOT / "examples/current-plan/portfolio.yaml").read_text(encoding="utf-8"))
_ROBOTICS_TARGET_ID = next(
    item["target_id"] for item in _PLAN["portfolio"]["allocation"]
    if item["isin"] == "IE00BYZK4552"
)
ROBOTICS_EXCEPTION = f"sensor.portfolio_architect_{_ROBOTICS_TARGET_ID}_accumulating_preferred_policy_exception"
LAST_EXCEPTION_DECISION = "date.portfolio_architect_last_exception_decision"
NEXT_EXCEPTION_REVIEW = "date.portfolio_architect_next_exception_review"
OVERDUE_EXCEPTION_REVIEW = "date.portfolio_architect_oldest_overdue_exception_review"
ACTIONABILITY = "sensor.portfolio_architect_plan_actionability"
RECOMMENDED_TOTAL = "sensor.portfolio_architect_recommended_total"
PURCHASE_COUNT = "sensor.portfolio_architect_purchase_count"


def _inner_entity(card: dict) -> str | None:
    if isinstance(card.get("entity"), str):
        return card["entity"]
    inner = card.get("card")
    if isinstance(inner, dict) and isinstance(inner.get("entity"), str):
        return inner["entity"]
    return None


def _inner_card(card: dict) -> dict:
    inner = card.get("card")
    return inner if isinstance(inner, dict) else card


def _policy_cards(view: dict) -> list[dict]:
    for section in view["sections"]:
        cards = section.get("cards", [])
        if any(
            card.get("type") == "heading"
            and card.get("heading")
            in {"Portfolio policy compliance", "Portfolio-Richtlinienkonformität"}
            for card in cards
        ):
            return [card for card in cards if card.get("type") != "heading"]
    raise AssertionError("policy section not found")


def _view(language: str) -> dict:
    document = yaml.safe_load(
        (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")
    )
    return next(view for view in document["views"] if view["title"] == language)


def _named_tiles(view: dict, name: str) -> list[dict]:
    found: list[dict] = []
    stack = [view]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if value.get("type") == "tile" and value.get("name") == name:
                found.append(value)
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return found


def test_german_unavailable_plan_values_use_available_actionability_proxy() -> None:
    german = _view("DE")
    allocated = _named_tiles(german, "Zugeordnet")
    purchases = _named_tiles(german, "Käufe")
    assert len(allocated) == 1
    assert len(purchases) == 1

    assert allocated[0]["entity"] == ACTIONABILITY
    assert allocated[0]["state_content"] == "recommended_total_display_de"
    assert allocated[0]["tap_action"] == {
        "action": "more-info",
        "entity": RECOMMENDED_TOTAL,
    }
    assert purchases[0]["entity"] == ACTIONABILITY
    assert purchases[0]["state_content"] == "purchase_count_display_de"
    assert purchases[0]["tap_action"] == {
        "action": "more-info",
        "entity": PURCHASE_COUNT,
    }


def test_actionability_sensor_owns_german_plan_value_proxy_attributes() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    block = sensor.split("class PortfolioPlanActionabilitySensor", 1)[1].split(
        "class _PortfolioPlanScheduleDateSensor", 1
    )[0]
    assert '"recommended_total_display_de"' in block
    assert '"purchase_count_display_de"' in block
    assert "available=self.coordinator.plan_actionable" in block
    # The underlying actionable entities keep their existing availability contract.
    recommended = sensor.split("class PortfolioRecommendedTotalSensor", 1)[1].split(
        "class PortfolioUnallocatedContributionSensor", 1
    )[0]
    purchases = sensor.split("class PortfolioPurchaseCountSensor", 1)[1].split(
        "class _PortfolioPlanEnumSensor", 1
    )[0]
    assert "requires_actionable_source = True" in recommended
    assert "self.coordinator.plan_actionable" in purchases


def test_policy_summary_keeps_aggregate_counters_out_of_primary_tiles() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    assert "class PortfolioPolicyChecksSensor" in sensor
    assert "class PortfolioOptimisationOpportunityCountSensor" in sensor

    for language in ("EN", "DE"):
        cards = _policy_cards(_view(language))
        entities = [_inner_entity(card) for card in cards]
        assert CHECKS not in entities
        # v1.29 may surface the opportunity count only as a compact heading badge;
        # it must not become a competing primary tile.
        assert OPPORTUNITIES not in entities
        assert EXCEPTIONS in entities
        policy_filters = [card for card in cards if card.get("type") == "entity-filter"]
        assert any("sensor.portfolio_architect_presentation_policy_001_finding" in card.get("entities", []) for card in policy_filters)


def test_policy_exception_lifecycle_tiles_are_coherently_ordered() -> None:
    for language in ("EN", "DE"):
        cards = _policy_cards(_view(language))
        entities = [_inner_entity(card) for card in cards]
        exception_index = entities.index(EXCEPTIONS)
        last_index = entities.index(LAST_EXCEPTION_DECISION)
        next_index = entities.index(NEXT_EXCEPTION_REVIEW)
        overdue_index = entities.index(OVERDUE_EXCEPTION_REVIEW)
        policy_index = next(
            index for index, card in enumerate(cards)
            if card.get("type") == "entity-filter"
            and "sensor.portfolio_architect_presentation_policy_001_finding" in card.get("entities", [])
        )

        assert exception_index < last_index
        assert last_index < next_index
        assert last_index < overdue_index
        assert {next_index, overdue_index} == {last_index + 1, last_index + 2}
        assert policy_index > max(next_index, overdue_index)


def test_policy_exception_lifecycle_labels_are_precise_in_both_languages() -> None:
    expected = {
        "EN": {
            LAST_EXCEPTION_DECISION: "Last decision",
            NEXT_EXCEPTION_REVIEW: "Exception review",
            OVERDUE_EXCEPTION_REVIEW: "Overdue review",
        },
        "DE": {
            LAST_EXCEPTION_DECISION: "Letzte Entscheidung",
            NEXT_EXCEPTION_REVIEW: "Ausnahmeprüfung",
            OVERDUE_EXCEPTION_REVIEW: "Überfällige Prüfung",
        },
    }
    for language, labels in expected.items():
        cards = _policy_cards(_view(language))
        by_entity = {_inner_entity(card): _inner_card(card) for card in cards}
        for entity, label in labels.items():
            assert by_entity[entity]["name"] == label


def test_concrete_policy_findings_remain_visible_through_generic_slot_contract() -> None:
    for language in ("EN", "DE"):
        cards = _policy_cards(_view(language))
        policy = next(
            card for card in cards
            if card.get("type") == "entity-filter"
            and "sensor.portfolio_architect_presentation_policy_001_finding" in card.get("entities", [])
        )
        assert len(policy["entities"]) == 256
        assert policy["card"]["type"] == "entities"
        assert policy["grid_options"]["columns"] == "full"
