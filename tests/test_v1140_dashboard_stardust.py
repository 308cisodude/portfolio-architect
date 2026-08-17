"""v1.14.0 native-dashboard Stardust layout contracts."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "dashboard"
EXCEPTION_ENTITY = (
    "sensor.portfolio_architect_robotics_accumulating_preferred_policy_exception"
)


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _exception_cards(path: Path) -> list[dict]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        node
        for node in _walk(document)
        if isinstance(node, dict)
        and node.get("type") == "conditional"
        and node.get("card", {}).get("entity") == EXCEPTION_ENTITY
    ]


def test_localised_exception_tiles_remain_compact() -> None:
    expected_names = {
        "en": {"Robotics exception", "Robotics review"},
        "de": {"Robotik-Ausnahme", "Robotik prüfen"},
    }
    for locale, names in expected_names.items():
        path = DASHBOARD / locale / "policy-compliance.yaml"
        cards = _exception_cards(path)
        assert len(cards) == 2
        assert {card["card"]["name"] for card in cards} == names
        for wrapper in cards:
            tile = wrapper["card"]
            assert wrapper["grid_options"]["columns"] == 6
            assert len(tile["name"]) <= 20
            assert tile["hide_state"] is True
            assert tile["color"] == "amber"


def test_complete_views_preserve_the_compact_exception_layout() -> None:
    for path in [
        DASHBOARD / "en" / "view.yaml",
        DASHBOARD / "de" / "view.yaml",
        DASHBOARD / "bilingual-dashboard.yaml",
    ]:
        cards = _exception_cards(path)
        expected = 4 if path.name == "bilingual-dashboard.yaml" else 2
        assert len(cards) == expected
        for wrapper in cards:
            tile = wrapper["card"]
            assert wrapper["grid_options"]["columns"] == 6
            assert "·" not in tile["name"]


def test_stardust_does_not_add_parallel_presentation() -> None:
    for path in DASHBOARD.rglob("*.yaml"):
        source = path.read_text(encoding="utf-8").casefold()
        assert "type: markdown" not in source, path
        assert "sensor.portfolio_architect_allocation_overview" not in source, path
