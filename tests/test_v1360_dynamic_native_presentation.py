"""v1.55.0 native dynamic portfolio-presentation contracts."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import re
import sys
import types

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(ROOT / "tests"))
from reference_portfolio import read_reference_positions
CURRENT_PLAN = ROOT / "examples" / "current-plan"
DASHBOARD = ROOT / "dashboard" / "bilingual-dashboard.yaml"


def _load_modules():
    package = types.ModuleType("pa_v136")
    package.__path__ = [str(COMPONENT)]
    sys.modules["pa_v136"] = package
    engine_path = COMPONENT / "engine" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "pa_v136.engine", engine_path, submodule_search_locations=[str(engine_path.parent)]
    )
    engine = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = engine
    assert spec.loader is not None
    spec.loader.exec_module(engine)
    for name in ("model", "presentation_slots", "portfolio_presentation"):
        path = COMPONENT / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"pa_v136.{name}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return engine, sys.modules["pa_v136.model"], sys.modules["pa_v136.portfolio_presentation"]


def _entities(value):
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"entity", "entity_id"}:
                if isinstance(child, str):
                    found.add(child)
                elif isinstance(child, list):
                    found.update(item for item in child if isinstance(item, str))
            found.update(_entities(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_entities(child))
    return found


def test_presentation_schema2_slots_reconcile_with_validated_current_state() -> None:
    engine, model, presentation = _load_modules()
    payload = engine.calculate_portfolio_payload_from_positions(
        read_reference_positions(),
        CURRENT_PLAN,
        evaluated_at=datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc),
        source_provider="generic_csv",
        source_label="Sanitized test fixture",
    )
    data = model.parse_portfolio_data(
        payload["recommendations"], payload["summary"], payload["policy_findings"], holdings=payload["holdings"]
    )
    result = presentation.build_portfolio_presentation(
        data, plan_actionable=True, actionability_reason="fresh"
    )
    assert result["presentation_schema_version"] == 2
    assert result["target_count"] == len(result["targets"])
    assert result["target_ids"] == [item["target_id"] for item in result["targets"]]
    assert [item["presentation_slot"] for item in result["targets"]] == list(
        range(1, result["target_count"] + 1)
    )
    assert all(item["slot_key"] == f"target_{item['presentation_slot']:02d}" for item in result["targets"])
    assert result["outside_scope_count"] == len(result["outside_scope_holdings"])
    assert result["outside_scope_position_ids"] == [
        item["position_id"] for item in result["outside_scope_holdings"]
    ]
    assert [item["presentation_slot"] for item in result["outside_scope_holdings"]] == list(
        range(1, result["outside_scope_count"] + 1)
    )
    assert result["active_policy_finding_count"] == len(result["active_policy_findings"])
    assert [item["presentation_slot"] for item in result["active_policy_findings"]] == list(
        range(1, result["active_policy_finding_count"] + 1)
    )


def test_reference_dashboard_has_no_instrument_specific_inventory() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert re.search(r"portfolio_architect_target_[0-9a-f]{32}_", source) is None
    assert "portfolio_architect_holding_" not in source
    assert "portfolio_architect_presentation_target_01_" in source
    assert "portfolio_architect_presentation_target_32_" in source
    assert "portfolio_architect_presentation_outside_001_" in source
    assert "portfolio_architect_presentation_outside_512_" in source
    assert "portfolio_architect_presentation_policy_001_finding" in source
    assert "portfolio_architect_presentation_policy_256_finding" in source


def test_reference_dashboard_uses_only_native_dynamic_cards() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    lowered = source.casefold()
    assert "type: entity-filter" in source
    assert "type: entities" in source
    # v1.55.0 retains native dynamic presentation while replacing the live-broken
    # entity-filter → Distribution composition with native Entities lists.
    assert "type: distribution" not in source
    assert "type: glance" in source
    for forbidden in ("auto-entities", "card-mod", "custom:", "javascript"):
        assert forbidden not in lowered

    doc = yaml.safe_load(source)
    assert len(doc["views"]) == 2
    assert _entities(doc["views"][0]) == _entities(doc["views"][1])


def test_dashboard_candidate_ranges_match_backend_bounds() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    target_slots = {int(value) for value in re.findall(r"presentation_target_(\d{2})_", source)}
    outside_slots = {int(value) for value in re.findall(r"presentation_outside_(\d{3})_", source)}
    policy_slots = {int(value) for value in re.findall(r"presentation_policy_(\d{3})_finding", source)}
    assert target_slots == set(range(1, 33))
    assert outside_slots == set(range(1, 513))
    assert policy_slots == set(range(1, 257))


def test_presentation_slots_are_explicitly_ephemeral_diagnostic_projection() -> None:
    slots = (COMPONENT / "presentation_slots.py").read_text(encoding="utf-8")
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    assert "Presentation slots are deliberately ephemeral UI projections" in slots
    assert "Slots must never be used as portfolio identity" in slots
    assert "PortfolioTargetPresentationSlotSensor" in sensor
    assert "PortfolioOutsidePresentationSlotSensor" in sensor
    assert "PortfolioPolicyPresentationSlotSensor" in sensor
    assert "PortfolioTargetPresentationSlotHeld" in binary
    # Presentation aliases are intentionally diagnostic and do not establish recorder measurement history.
    target_block = sensor.split("class PortfolioTargetPresentationSlotSensor", 1)[1].split(
        "class PortfolioOutsidePresentationSlotSensor", 1
    )[0]
    assert "EntityCategory.DIAGNOSTIC" in target_block
    assert "SensorStateClass" not in target_block
    assert '"stable_identity": position.target_id' in target_block


def test_current_version_metadata_is_aligned() -> None:
    assert 'version = "1.55.0"' in (ROOT / "pyproject.toml").read_text()
    assert '"version": "1.55.0"' in (COMPONENT / "manifest.json").read_text()
    assert 'VERSION: Final = "1.55.0"' in (COMPONENT / "const.py").read_text()
    assert '__version__ = "1.55.0"' in (COMPONENT / "engine" / "__init__.py").read_text()
    for app in (
        "portfolio_architect_gateway",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
    ):
        config = yaml.safe_load((ROOT / "home_assistant_app" / app / "config.yaml").read_text())
        assert config["version"] == "1.55.0"
