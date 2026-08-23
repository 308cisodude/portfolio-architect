"""v1.38.1 native dynamic allocation-drift presentation contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re
from collections import Counter, defaultdict

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
DASHBOARD = ROOT / "dashboard" / "bilingual-dashboard.yaml"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _drift_conditionals(view: dict) -> list[dict]:
    return [
        item
        for item in _walk(view)
        if item.get("type") == "conditional"
        and isinstance(item.get("card"), dict)
        and str(item["card"].get("entity", "")).endswith("_allocation_drift")
    ]


def test_each_locale_has_32_bounded_target_slots_with_three_native_status_variants() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    expected = {"underweight": "amber", "on_target": "green", "overweight": "red"}

    for view in doc["views"]:
        conditionals = _drift_conditionals(view)
        assert len(conditionals) == 32 * 3
        by_slot: dict[int, set[str]] = defaultdict(set)
        seen_pairs: Counter[tuple[int, str]] = Counter()
        for wrapper in conditionals:
            assert len(wrapper["conditions"]) == 1
            condition = wrapper["conditions"][0]
            assert condition["condition"] == "state"
            match = re.fullmatch(
                r"sensor\.portfolio_architect_presentation_target_(\d{2})_allocation_status",
                condition["entity"],
            )
            assert match is not None
            slot = int(match.group(1))
            status = condition["state"]
            assert status in expected
            assert wrapper["card"]["color"] == expected[status]
            by_slot[slot].add(status)
            seen_pairs[(slot, status)] += 1

        assert set(by_slot) == set(range(1, 33))
        assert all(states == set(expected) for states in by_slot.values())
        assert all(count == 1 for count in seen_pairs.values())


def test_drift_tiles_use_dynamic_entity_names_and_signed_native_bar_gauge() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    for view in doc["views"]:
        for wrapper in _drift_conditionals(view):
            card = wrapper["card"]
            assert card["type"] == "tile"
            assert card["name"] == {"type": "entity"}
            assert card["features"] == [{"type": "bar-gauge", "min": -100, "max": 100}]
            assert wrapper["grid_options"] == {"columns": "full", "rows": "auto"}

            slot = re.search(r"target_(\d{2})_allocation_drift$", card["entity"])
            assert slot is not None
            prefix = f"sensor.portfolio_architect_presentation_target_{slot.group(1)}"
            assert card["entity"] == f"{prefix}_allocation_drift"
            assert wrapper["conditions"][0]["entity"] == f"{prefix}_allocation_status"


def test_drift_tile_tap_opens_matching_bounded_explanation_without_custom_inventory() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    doc = yaml.safe_load(source)
    for view in doc["views"]:
        for wrapper in _drift_conditionals(view):
            card = wrapper["card"]
            slot = re.search(r"target_(\d{2})_allocation_drift$", card["entity"])
            assert slot is not None
            prefix = f"sensor.portfolio_architect_presentation_target_{slot.group(1)}"
            assert card["tap_action"] == {
                "action": "more-info",
                "entity": f"{prefix}_allocation_explanation",
            }

    lowered = source.casefold()
    for forbidden in ("auto-entities", "card-mod", "custom:", "javascript"):
        assert forbidden not in lowered
    assert re.search(r"portfolio_architect_target_[0-9a-f]{32}_", source) is None
    assert "portfolio_architect_holding_" not in source


def test_v1380_cash_context_and_copy_friendly_purchase_interaction_are_preserved() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    expected_cash = (
        (
            "Authorized investment cash",
            "Cash after recommended purchases",
            ["state", "cash_context"],
            "Recommended purchases",
        ),
        (
            "Freigegebenes Anlageguthaben",
            "Guthaben nach empfohlenen Käufen",
            ["display_state_de", "cash_context_de"],
            "Empfohlene Käufe",
        ),
    )

    for view, (authorized_name, remaining_name, state_content, purchase_title) in zip(
        doc["views"], expected_cash, strict=True
    ):
        cards = list(_walk(view))
        authorized = [item for item in cards if item.get("name") == authorized_name]
        remaining = [item for item in cards if item.get("name") == remaining_name]
        assert len(authorized) == len(remaining) == 1
        assert authorized[0]["state_content"] == state_content
        assert remaining[0]["state_content"] == state_content

        filters = [
            item
            for item in cards
            if item.get("type") == "entity-filter"
            and isinstance(item.get("card"), dict)
            and item["card"].get("title") == purchase_title
        ]
        assert len(filters) == 1
        rows = filters[0]["entities"]
        assert len(rows) == 32
        for slot, row in enumerate(rows, start=1):
            prefix = f"sensor.portfolio_architect_presentation_target_{slot:02d}"
            assert row["entity"] == f"{prefix}_proposed_buy"
            assert row["tap_action"]["entity"] == f"{prefix}_instrument_isin"
            assert row["hold_action"]["entity"] == f"{prefix}_purchase_explanation"


def test_v1381_release_metadata_notes_and_wire_contracts_are_aligned() -> None:
    assert 'version = "1.47.0"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.47.0"
    assert 'VERSION: Final = "1.47.0"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert '__version__ = "1.47.0"' in (COMPONENT / "engine" / "__init__.py").read_text(encoding="utf-8")
    for app in (
        "portfolio_architect_gateway",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
    ):
        config = yaml.safe_load((ROOT / "home_assistant_app" / app / "config.yaml").read_text())
        assert config["version"] == "1.47.0"

    assert (ROOT / "docs" / "UPGRADE-1.38.1.md").is_file()
    release_notes = (ROOT / "docs" / "RELEASE-NOTES.md").read_text(encoding="utf-8")
    assert "not included" in release_notes
    assert "intentionally absent" not in release_notes
    for contract in (
        "payload schema 8: unchanged",
        "REST portfolio schema 1: unchanged",
        "Gateway health schema 6: unchanged",
        "presentation schema 2",
        "broker schemas 1/2/3",
    ):
        assert contract in release_notes
