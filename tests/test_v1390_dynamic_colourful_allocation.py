"""v1.39.0 dynamic colourful allocation presentation contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re
from collections import defaultdict

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
DASHBOARD = ROOT / "dashboard" / "bilingual-dashboard.yaml"
PALETTE = (
    "blue",
    "teal",
    "purple",
    "light-blue",
    "pink",
    "orange",
    "indigo",
    "cyan",
    "deep-purple",
    "lime",
    "deep-orange",
    "blue-grey",
    "brown",
    "yellow",
    "light-green",
    "grey",
)


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _allocation_conditionals(view: dict) -> list[dict]:
    return [
        item
        for item in _walk(view)
        if item.get("type") == "conditional"
        and isinstance(item.get("card"), dict)
        and re.fullmatch(
            r"sensor\.portfolio_architect_presentation_target_\d{2}_(?:current|target)_allocation",
            str(item["card"].get("entity", "")),
        )
    ]


def _drift_conditionals(view: dict) -> list[dict]:
    return [
        item
        for item in _walk(view)
        if item.get("type") == "conditional"
        and isinstance(item.get("card"), dict)
        and str(item["card"].get("entity", "")).endswith("_allocation_drift")
    ]


def test_each_locale_has_paired_colourful_current_and_target_tiles_for_32_slots() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))

    for view in doc["views"]:
        conditionals = _allocation_conditionals(view)
        assert len(conditionals) == 32 * 2
        by_slot: dict[int, dict[str, dict]] = defaultdict(dict)
        for wrapper in conditionals:
            card = wrapper["card"]
            match = re.fullmatch(
                r"sensor\.portfolio_architect_presentation_target_(\d{2})_(current|target)_allocation",
                card["entity"],
            )
            assert match is not None
            slot = int(match.group(1))
            kind = match.group(2)
            assert kind not in by_slot[slot]
            by_slot[slot][kind] = wrapper

        assert set(by_slot) == set(range(1, 33))
        for slot, pair in by_slot.items():
            assert set(pair) == {"current", "target"}
            expected_color = PALETTE[(slot - 1) % len(PALETTE)]
            for kind, wrapper in pair.items():
                prefix = f"sensor.portfolio_architect_presentation_target_{slot:02d}"
                assert wrapper["conditions"] == [
                    {
                        "condition": "numeric_state",
                        "entity": f"{prefix}_target_allocation",
                        "above": 0,
                    }
                ]
                card = wrapper["card"]
                assert card["type"] == "tile"
                assert card["entity"] == f"{prefix}_{kind}_allocation"
                assert card["name"] == {"type": "entity"}
                assert card["color"] == expected_color
                assert card["tap_action"] == {"action": "more-info"}
                assert card["features"] == [{"type": "bar-gauge", "min": 0, "max": 100}]
                assert wrapper["grid_options"] == {"columns": "full", "rows": "auto"}


def test_current_tile_visibility_is_keyed_to_target_membership_not_current_weight() -> None:
    """A configured-but-missing target must still render as a 0% current tile."""
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    for view in doc["views"]:
        for wrapper in _allocation_conditionals(view):
            card_entity = wrapper["card"]["entity"]
            if card_entity.endswith("_current_allocation"):
                condition_entity = wrapper["conditions"][0]["entity"]
                assert condition_entity == card_entity.replace(
                    "_current_allocation", "_target_allocation"
                )


def test_old_current_target_entity_filter_lists_are_removed_without_touching_drift() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    obsolete_titles = {
        "Current plan allocation",
        "Plan target allocation",
        "Aktuelle Planallokation",
        "Zielallokation des Plans",
    }
    for item in _walk(doc):
        if item.get("type") == "entity-filter" and isinstance(item.get("card"), dict):
            assert item["card"].get("title") not in obsolete_titles

    # v1.39.0's live-accepted semantic drift language is intentionally unchanged.
    for view in doc["views"]:
        drift = _drift_conditionals(view)
        assert len(drift) == 32 * 3
        for wrapper in drift:
            status = wrapper["conditions"][0]["state"]
            assert wrapper["card"]["color"] == {
                "underweight": "amber",
                "on_target": "green",
                "overweight": "red",
            }[status]
            assert wrapper["card"]["features"] == [
                {"type": "bar-gauge", "min": -100, "max": 100}
            ]


def test_colour_is_slot_identity_only_and_dashboard_remains_generic_native_only() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    lowered = source.casefold()
    for forbidden in ("auto-entities", "card-mod", "custom:", "javascript"):
        assert forbidden not in lowered
    assert re.search(r"portfolio_architect_target_[0-9a-f]{32}_", source) is None
    assert "portfolio_architect_holding_" not in source
    assert "IE00" not in source
    assert "Robotics" not in source
    assert "Robotik" not in source


def test_v1390_release_metadata_and_preserved_contracts_are_aligned() -> None:
    assert 'version = "1.46.0"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.46.0"
    assert 'VERSION: Final = "1.46.0"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert '__version__ = "1.46.0"' in (COMPONENT / "engine" / "__init__.py").read_text(encoding="utf-8")
    for app in (
        "portfolio_architect_gateway",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
    ):
        config = yaml.safe_load((ROOT / "home_assistant_app" / app / "config.yaml").read_text())
        assert config["version"] == "1.46.0"

    assert (ROOT / "docs" / "UPGRADE-1.46.0.md").is_file()
    release_notes = (ROOT / "docs" / "RELEASE-NOTES.md").read_text(encoding="utf-8")
    for contract in (
        "payload schema 8: unchanged",
        "REST portfolio schema 1: unchanged",
        "Gateway health schema 6: unchanged",
        "presentation schema 2",
        "broker schemas 1/2/3",
    ):
        assert contract in release_notes
