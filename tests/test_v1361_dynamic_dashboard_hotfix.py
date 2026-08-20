"""v1.36.1 live-observed native-dashboard presentation hotfix contracts."""

from __future__ import annotations

from pathlib import Path
import re

import yaml

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "dashboard" / "bilingual-dashboard.yaml"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _entity_filters(doc):
    return [item for item in _walk(doc) if item.get("type") == "entity-filter"]


def _entity_id(item):
    return item["entity"] if isinstance(item, dict) else item


def _dynamic_candidates(filters):
    for wrapper in filters:
        for candidate in wrapper["entities"]:
            entity = _entity_id(candidate)
            if "portfolio_architect_presentation_" in entity:
                yield wrapper, candidate, entity


def test_live_broken_distribution_composition_is_removed() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "type: distribution" not in source
    assert "Whole-portfolio distribution" not in source
    assert "Verteilung des Gesamtportfolios" not in source


def test_dynamic_allocation_filters_feed_native_entities_lists() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    filters = _entity_filters(doc)
    by_title = {wrapper["card"].get("title"): wrapper for wrapper in filters}
    expected = {
        "Whole-portfolio allocation": 544,
        "Allokation des Gesamtportfolios": 544,
    }
    for title, count in expected.items():
        wrapper = by_title[title]
        assert wrapper["card"]["type"] == "entities"
        assert wrapper["card"]["show_header_toggle"] is False
        assert wrapper["show_empty"] is False
        assert wrapper["conditions"] == [{"condition": "numeric_state", "above": 0}]
        assert len(wrapper["entities"]) == count


def test_dynamic_candidates_request_entity_only_names() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    filters = _entity_filters(doc)
    seen = 0
    for _wrapper, candidate, _entity in _dynamic_candidates(filters):
        assert isinstance(candidate, dict)
        assert candidate.get("name") == {"type": "entity"}
        seen += 1

    # v1.39.0 replaces the former 3 × 32 allocation-status entity-filter rows per
    # locale with native Conditional + Tile cards. v1.39.0 likewise moves the
    # current/target allocation rows to paired Conditional + Tile cards.
    drift_tiles = [
        item["card"]
        for item in _walk(doc)
        if item.get("type") == "conditional"
        and isinstance(item.get("card"), dict)
        and str(item["card"].get("entity", "")).endswith("_allocation_drift")
    ]
    assert len(drift_tiles) == 192
    assert all(tile.get("name") == {"type": "entity"} for tile in drift_tiles)
    allocation_tiles = [
        item["card"]
        for item in _walk(doc)
        if item.get("type") == "conditional"
        and isinstance(item.get("card"), dict)
        and str(item["card"].get("entity", "")).endswith(("_current_allocation", "_target_allocation"))
    ]
    assert len(allocation_tiles) == 128
    assert all(tile.get("name") == {"type": "entity"} for tile in allocation_tiles)
    # EN and DE still enumerate the same 1,600 bounded dynamic candidates each.
    assert seen + len(drift_tiles) + len(allocation_tiles) == 3200


def test_conditioned_candidates_keep_per_entity_conditions() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    allocation_status_cards = [
        item
        for item in _walk(doc)
        if item.get("type") == "conditional"
        and isinstance(item.get("card"), dict)
        and str(item["card"].get("entity", "")).endswith("_allocation_drift")
    ]
    assert len(allocation_status_cards) == 192
    expected = {"underweight": "amber", "on_target": "green", "overweight": "red"}
    for wrapper in allocation_status_cards:
        assert len(wrapper["conditions"]) == 1
        condition = wrapper["conditions"][0]
        assert condition["condition"] == "state"
        assert condition["entity"].endswith("_allocation_status")
        assert condition["state"] in expected
        assert wrapper["card"]["color"] == expected[condition["state"]]
        assert wrapper["card"]["name"] == {"type": "entity"}


def test_hotfix_preserves_dynamic_bounds_and_no_instrument_inventory() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    target_slots = {int(value) for value in re.findall(r"presentation_target_(\d{2})_", source)}
    outside_slots = {int(value) for value in re.findall(r"presentation_outside_(\d{3})_", source)}
    policy_slots = {int(value) for value in re.findall(r"presentation_policy_(\d{3})_finding", source)}
    assert target_slots == set(range(1, 33))
    assert outside_slots == set(range(1, 513))
    assert policy_slots == set(range(1, 257))
    assert re.search(r"portfolio_architect_target_[0-9a-f]{32}_", source) is None
    assert "portfolio_architect_holding_" not in source


def test_hotfix_preserves_presentation_schema2_backend() -> None:
    presentation = (ROOT / "custom_components" / "portfolio_architect" / "portfolio_presentation.py").read_text(
        encoding="utf-8"
    )
    slots = (ROOT / "custom_components" / "portfolio_architect" / "presentation_slots.py").read_text(
        encoding="utf-8"
    )
    assert 'PRESENTATION_SCHEMA_VERSION = 2' in presentation
    assert "MAX_TARGET_PRESENTATION_SLOTS = MAX_POSITIONS" in slots
    assert "MAX_OUTSIDE_PRESENTATION_SLOTS = MAX_HOLDINGS" in slots
    assert "MAX_POLICY_PRESENTATION_SLOTS = MAX_POLICY_FINDINGS" in slots
    model = (ROOT / "custom_components" / "portfolio_architect" / "model.py").read_text(encoding="utf-8")
    assert "MAX_POSITIONS = 32" in model
    assert "MAX_HOLDINGS = 512" in model
    assert "MAX_POLICY_FINDINGS = 256" in model
