from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
OPPORTUNITY_COUNT = "sensor.portfolio_architect_optimisation_opportunity_count"
_PLAN = yaml.safe_load((ROOT / "examples/current-plan/portfolio.yaml").read_text(encoding="utf-8"))
_WORLD_TARGET_ID = next(
    item["target_id"] for item in _PLAN["portfolio"]["allocation"]
    if item["isin"] == "IE00BJ0KDQ92"
)
WORLD_OPPORTUNITY = f"sensor.portfolio_architect_{_WORLD_TARGET_ID}_free_savings_plan_preferred_policy_finding"
REVIEW_ENTITIES = {
    "date.portfolio_architect_next_exception_review",
    "date.portfolio_architect_oldest_overdue_exception_review",
}


def _inner(card: dict) -> dict:
    inner = card.get("card")
    return inner if isinstance(inner, dict) else card


def _entity(card: dict) -> str | None:
    inner = _inner(card)
    entity = inner.get("entity")
    return entity if isinstance(entity, str) else None


def _policy_section_cards(view: dict) -> list[dict]:
    headings = {"Portfolio policy compliance", "Portfolio-Richtlinienkonformität"}
    for section in view["sections"]:
        cards = section.get("cards", [])
        if any(card.get("type") == "heading" and card.get("heading") in headings for card in cards):
            return cards
    raise AssertionError("policy section not found")


def _standalone_cards(locale: str) -> list[dict]:
    doc = yaml.safe_load((DASHBOARD / locale / "policy-compliance.yaml").read_text(encoding="utf-8"))
    return doc["cards"]


def _view_cards(locale: str) -> list[dict]:
    doc = yaml.safe_load((DASHBOARD / locale / "view.yaml").read_text(encoding="utf-8"))
    return _policy_section_cards(doc)


def _bilingual_cards(title: str) -> list[dict]:
    doc = yaml.safe_load((DASHBOARD / "bilingual-dashboard.yaml").read_text(encoding="utf-8"))
    view = next(view for view in doc["views"] if view["title"] == title)
    return _policy_section_cards(view)


def _candidate_entity(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        entity = value.get("entity")
        return entity if isinstance(entity, str) else None
    return None


def _assert_opportunity_heading(cards: list[dict], expected_heading: str) -> None:
    candidates = [
        (index, card)
        for index, card in enumerate(cards)
        if _inner(card).get("type") == "heading"
        and _inner(card).get("heading") == expected_heading
    ]
    assert len(candidates) == 1
    heading_index, wrapper = candidates[0]
    heading = _inner(wrapper)

    assert wrapper.get("type") == "conditional"
    assert wrapper.get("conditions") == [{
        "condition": "numeric_state",
        "entity": OPPORTUNITY_COUNT,
        "above": 0,
    }]
    assert wrapper.get("grid_options") == {"columns": "full", "rows": "auto"}
    assert heading.get("heading_style") == "subtitle"
    assert heading.get("icon") == "mdi:lightbulb-on-outline"
    assert heading.get("badges") == [{
        "type": "entity",
        "entity": OPPORTUNITY_COUNT,
        "show_icon": False,
        "show_state": True,
        "tap_action": {"action": "more-info"},
    }]

    review_indexes = [index for index, card in enumerate(cards) if _entity(card) in REVIEW_ENTITIES]
    policy_indexes = [
        index for index, card in enumerate(cards)
        if card.get("type") == "entity-filter"
        and any(_candidate_entity(item) == "sensor.portfolio_architect_presentation_policy_001_finding" for item in card.get("entities", []))
    ]
    assert len(review_indexes) == 2
    assert len(policy_indexes) == 1
    assert max(review_indexes) < heading_index < policy_indexes[0]
    policy = cards[policy_indexes[0]]
    assert len(policy["entities"]) == 256
    assert policy["card"]["type"] == "entities"
    assert policy["grid_options"]["columns"] == "full"


def test_policy_opportunity_hierarchy_is_native_localised_and_consistent() -> None:
    cases = (
        ("en", "EN", "Optimisation opportunities"),
        ("de", "DE", "Optimierungsmöglichkeiten"),
    )
    for locale, title, heading in cases:
        _assert_opportunity_heading(_standalone_cards(locale), heading)
        _assert_opportunity_heading(_view_cards(locale), heading)
        _assert_opportunity_heading(_bilingual_cards(title), heading)


def test_policy_polish_uses_no_custom_or_markdown_card_surface() -> None:
    for path in (
        DASHBOARD / "en" / "policy-compliance.yaml",
        DASHBOARD / "de" / "policy-compliance.yaml",
        DASHBOARD / "bilingual-dashboard.yaml",
    ):
        source = path.read_text(encoding="utf-8").casefold()
        assert "card_mod" not in source
        assert "custom:" not in source
        if "type: markdown" in source:
            assert "sensor.portfolio_architect_execution_path" in source
