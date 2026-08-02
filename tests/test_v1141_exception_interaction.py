"""v1.15.0 accepted-exception interaction contracts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "dashboard"
DETAIL_ENTITY = (
    "sensor.portfolio_architect_robotics_accumulating_preferred_policy_exception"
)
ORIGINAL_ENTITY = (
    "sensor.portfolio_architect_robotics_accumulating_preferred_policy_finding"
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
        and node.get("card", {}).get("entity") == DETAIL_ENTITY
    ]


def test_exception_tile_is_compact_clickable_and_bounded() -> None:
    expected_names = {"en": "Robotics exception", "de": "Robotik-Ausnahme"}
    for locale, expected_name in expected_names.items():
        cards = _exception_cards(DASHBOARD / locale / "policy-compliance.yaml")
        assert len(cards) == 1
        wrapper = cards[0]
        tile = wrapper["card"]
        assert wrapper["grid_options"]["columns"] == 6
        assert tile["name"] == expected_name
        assert tile["tap_action"] == {"action": "more-info"}
        assert tile["hide_state"] is True
        assert tile["color"] == "amber"
        assert wrapper["conditions"][0]["entity"] == DETAIL_ENTITY


def test_complete_views_use_the_bounded_detail_entity() -> None:
    for path in [
        DASHBOARD / "en" / "view.yaml",
        DASHBOARD / "de" / "view.yaml",
        DASHBOARD / "bilingual-dashboard.yaml",
    ]:
        cards = _exception_cards(path)
        expected = 2 if path.name == "bilingual-dashboard.yaml" else 1
        assert len(cards) == expected
        for wrapper in cards:
            assert wrapper["card"]["tap_action"] == {"action": "more-info"}
        source = path.read_text(encoding="utf-8")
        assert ORIGINAL_ENTITY not in source


def test_bounded_detail_entity_omits_long_rationale() -> None:
    sensor = (ROOT / "custom_components/portfolio_architect/sensor.py").read_text()
    model = (ROOT / "custom_components/portfolio_architect/model.py").read_text()
    assert "class PortfolioPolicyExceptionDetailSensor" in sensor
    assert 'object_id(self) -> str:' in sensor
    assert "exception_detail_attributes" in model
    detail_section = model.split("def exception_detail_attributes", 1)[1].split("@dataclass", 1)[0]
    assert "exception_rationale" not in detail_section


def test_exception_detail_translations_are_complete() -> None:
    for locale in ("en", "de"):
        data = json.loads(
            (ROOT / "custom_components/portfolio_architect/translations" / f"{locale}.json")
            .read_text(encoding="utf-8")
        )
        detail = data["entity"]["sensor"]["policy_exception_detail"]
        assert detail["state"]["accepted_exception"]
        assert set(detail["state_attributes"]) == {
            "fund_name", "rule", "observed", "expected", "decision_on", "review_on"
        }
