"""v1.35.0 whole-portfolio allocation presentation regressions."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import types

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
CURRENT_PLAN = ROOT / "examples" / "current-plan"

OUTSIDE_ALLOCATION_IDS = {
    "holding_de0005557508",
    "holding_de0007664005",
    "holding_ie00bm67ht60",
    "holding_de000a1x3w34",
    "holding_us61945m1018",
    "holding_us19260q1076",
    "holding_de000a3e5a59",
    "holding_ie00bywz0333",
}
OBSOLETE_WKN_ALLOCATION_IDS = {
    "holding_555750",
    "holding_766400",
    "holding_a113fm",
    "holding_a1x3w3",
    "holding_a2qkff",
    "holding_a2qp7j",
    "holding_a3e5a5",
}


def _load_engine_package():
    package = types.ModuleType("pa_v1341")
    package.__path__ = [str(COMPONENT)]
    sys.modules["pa_v1341"] = package
    engine_path = COMPONENT / "engine" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "pa_v1341.engine", engine_path, submodule_search_locations=[str(engine_path.parent)]
    )
    engine = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = engine
    assert spec.loader is not None
    spec.loader.exec_module(engine)
    return engine


def test_missing_target_has_defined_zero_whole_portfolio_allocation() -> None:
    engine = _load_engine_package()
    payload = engine.calculate_portfolio_payload(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv",
        CURRENT_PLAN,
        evaluated_at=datetime(2026, 8, 18, 19, 30, tzinfo=timezone.utc),
    )
    robotics = next(
        item for item in payload["recommendations"] if item["isin"] == "IE00BYZK4552"
    )
    assert robotics["current_value_eur"] == 0
    assert robotics["whole_portfolio_pct"] == 0
    assert robotics["target_pct"] == 5


def test_target_whole_allocation_entity_is_created_from_target_state_not_holding_presence() -> None:
    source = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    assert "class PortfolioTargetWholeAllocationSensor" in source
    assert 'self._attr_unique_id = f"{source_key}_{fund_id}_whole_portfolio_allocation"' in source
    assert 'return f"{self._fund_id}_whole_portfolio_allocation"' in source
    assert "return self._position.whole_portfolio_pct if self.available else None" in source
    setup = source[source.index("def _add_missing_entities"):source.index("class PortfolioPresentationModelSensor")]
    assert "PortfolioTargetWholeAllocationSensor(" in setup
    assert "position.is_target_position and fund_id not in known_whole_allocations" in setup
    assert "if position_id not in known_whole_allocations:" in setup
    # Existing held targets and newly missing targets therefore share the established
    # target-ID entity identity without creating a duplicate holding allocation entity.
    assert "known_whole_allocations.add(fund_id)" in setup


def test_reference_distribution_uses_current_isin_first_outside_holding_ids() -> None:
    paths = (
        ROOT / "dashboard" / "allocation-stack.yaml",
        ROOT / "dashboard" / "en" / "allocation-stack.yaml",
        ROOT / "dashboard" / "de" / "allocation-stack.yaml",
        ROOT / "dashboard" / ".tmp_en.yaml",
        ROOT / "dashboard" / ".tmp_de.yaml",
        ROOT / "dashboard" / "en" / "view.yaml",
        ROOT / "dashboard" / "de" / "view.yaml",
        ROOT / "dashboard" / "bilingual-dashboard.yaml",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for position_id in OUTSIDE_ALLOCATION_IDS:
            assert f"sensor.portfolio_architect_{position_id}_whole_portfolio_allocation" in text, path
        for obsolete in OBSOLETE_WKN_ALLOCATION_IDS:
            assert f"sensor.portfolio_architect_{obsolete}_whole_portfolio_allocation" not in text, path


def test_v1341_does_not_make_outside_scope_tile_inventory_dynamic_yet() -> None:
    presentation = yaml.safe_load((CURRENT_PLAN / "portfolio.yaml").read_text(encoding="utf-8"))
    assert presentation["schema_version"] == 2
    dashboard = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")
    # The hard-coded outside-scope detail inventory is deliberately retained until the
    # later dynamic native-dashboard milestone. v1.35.0 fixes its ISIN-first bindings
    # plus distribution correctness and the missing-target 0% entity.
    assert "sensor.portfolio_architect_holding_ie00bywz0333_holding_value" in dashboard
    assert "auto-entities" not in dashboard.casefold()
    assert "custom:" not in dashboard.casefold()
