"""v1.15.0 accepted-exception interaction contracts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "dashboard"
_PLAN = yaml.safe_load((ROOT / "examples/current-plan/portfolio.yaml").read_text(encoding="utf-8"))
_ROBOTICS_TARGET_ID = next(
    item["target_id"] for item in _PLAN["portfolio"]["allocation"]
    if item["isin"] == "IE00BYZK4552"
)
DETAIL_ENTITY = f"sensor.portfolio_architect_{_ROBOTICS_TARGET_ID}_accumulating_preferred_policy_exception"
ORIGINAL_ENTITY = f"sensor.portfolio_architect_{_ROBOTICS_TARGET_ID}_accumulating_preferred_policy_finding"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _policy_slot_filters(path: Path) -> list[dict]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        node for node in _walk(document)
        if isinstance(node, dict)
        and node.get("type") == "entity-filter"
        and "sensor.portfolio_architect_presentation_policy_001_finding" in node.get("entities", [])
    ]


def test_exception_presentation_is_clickable_bounded_native_list() -> None:
    for locale in ("en", "de"):
        cards = _policy_slot_filters(DASHBOARD / locale / "policy-compliance.yaml")
        assert len(cards) == 1
        wrapper = cards[0]
        assert len(wrapper["entities"]) == 256
        assert wrapper["card"]["type"] == "entities"
        assert wrapper["show_empty"] is False
        assert wrapper["grid_options"]["columns"] == "full"


def test_complete_views_use_generic_bounded_policy_detail_aliases() -> None:
    for path in [
        DASHBOARD / "en" / "view.yaml",
        DASHBOARD / "de" / "view.yaml",
        DASHBOARD / "bilingual-dashboard.yaml",
    ]:
        cards = _policy_slot_filters(path)
        expected = 2 if path.name == "bilingual-dashboard.yaml" else 1
        assert len(cards) == expected
        source = path.read_text(encoding="utf-8")
        assert ORIGINAL_ENTITY not in source
        assert DETAIL_ENTITY not in source
        assert "presentation_policy_001_finding" in source


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
            "fund_name",
            "rule",
            "observed",
            "expected",
            "decision_on",
            "review_on",
            "review_reason",
            "expected_provider",
            "observed_provider",
        }
