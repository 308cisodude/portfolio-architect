"""v1.14.0 native-dashboard Stardust layout contracts."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "dashboard"
_PLAN = yaml.safe_load((ROOT / "examples/current-plan/portfolio.yaml").read_text(encoding="utf-8"))
_ROBOTICS_TARGET_ID = next(
    item["target_id"]
    for item in _PLAN["portfolio"]["allocation"]
    if item["isin"] == "IE00BYZK4552"
)
EXCEPTION_ENTITY = (
    f"sensor.portfolio_architect_{_ROBOTICS_TARGET_ID}_accumulating_preferred_policy_exception"
)


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


def _policy_slot_filters(path: Path) -> list[dict]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        node for node in _walk(document)
        if isinstance(node, dict)
        and node.get("type") == "entity-filter"
        and any(
            (_candidate_entity(entity) or "").startswith("sensor.portfolio_architect_presentation_policy_")
            for entity in node.get("entities", [])
        )
    ]


def test_localised_exception_presentation_is_bounded_native_list() -> None:
    for locale in ("en", "de"):
        cards = _policy_slot_filters(DASHBOARD / locale / "policy-compliance.yaml")
        assert len(cards) == 1
        card = cards[0]
        assert len(card["entities"]) == 256
        assert _candidate_entity(card["entities"][0]) == "sensor.portfolio_architect_presentation_policy_001_finding"
        assert _candidate_entity(card["entities"][-1]) == "sensor.portfolio_architect_presentation_policy_256_finding"
        assert card["card"]["type"] == "entities"
        assert card["grid_options"]["columns"] == "full"
        assert card["show_empty"] is False


def test_complete_views_preserve_bounded_native_policy_presentation() -> None:
    for path in [
        DASHBOARD / "en" / "view.yaml",
        DASHBOARD / "de" / "view.yaml",
        DASHBOARD / "bilingual-dashboard.yaml",
    ]:
        cards = _policy_slot_filters(path)
        expected = 2 if path.name == "bilingual-dashboard.yaml" else 1
        assert len(cards) == expected
        assert all(card["card"]["type"] == "entities" for card in cards)


def test_stardust_does_not_add_parallel_presentation() -> None:
    for path in DASHBOARD.rglob("*.yaml"):
        source = path.read_text(encoding="utf-8").casefold()
        assert "type: markdown" not in source, path
        assert "sensor.portfolio_architect_allocation_overview" not in source, path
