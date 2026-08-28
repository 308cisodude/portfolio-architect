"""v1.55.0 regression contracts for the all-Gateway coordinator source metadata."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
COORDINATOR = COMPONENT / "coordinator.py"
BINARY_SENSOR = COMPONENT / "binary_sensor.py"


def _load_configuration_label_owner() -> type:
    """Compile the exact production property without importing Home Assistant."""
    tree = ast.parse(COORDINATOR.read_text(encoding="utf-8"))
    coordinator_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PortfolioArchitectCoordinator"
    )
    method = next(
        node
        for node in coordinator_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "configuration_label"
    )
    isolated = ast.ClassDef(
        name="CoordinatorPropertyHarness",
        bases=[],
        keywords=[],
        body=[method],
        decorator_list=[],
    )
    module = ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[]))
    namespace: dict[str, object] = {}
    exec(compile(module, str(COORDINATOR), "exec"), namespace)
    return namespace["CoordinatorPropertyHarness"]  # type: ignore[return-value]


def _load_source_attributes():
    """Compile the exact production helper without importing Home Assistant."""
    tree = ast.parse(BINARY_SENSOR.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_source_attributes"
    )
    # The production module uses postponed annotations. The isolated harness does
    # not need its Home Assistant-only type names, so remove only annotations while
    # preserving the exact executable body.
    function.returns = None
    for argument in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs):
        argument.annotation = None
    namespace = {
        "_isoformat": lambda value: value.isoformat() if value is not None else None,
    }
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(module, str(BINARY_SENSOR), "exec"), namespace)
    return namespace["_source_attributes"]


def test_all_gateway_configuration_label_has_no_removed_local_file_dependency() -> None:
    coordinator_source = COORDINATOR.read_text(encoding="utf-8")
    assert "self.local_paths" not in coordinator_source
    assert "self.csv_source_config" not in coordinator_source

    harness = _load_configuration_label_owner()
    coordinator = harness()
    coordinator.configuration_path = SimpleNamespace(config_relative="portfolio-architect")
    assert coordinator.configuration_label == "portfolio-architect"

    coordinator.configuration_path = None
    assert coordinator.configuration_label is None


def test_schema12_all_gateway_source_attributes_execute_without_local_paths_member() -> None:
    """Reproduce the v1.55.0 live entity-attribute call on an all-Gateway object."""
    harness = _load_configuration_label_owner()
    coordinator = harness()
    coordinator.configuration_path = SimpleNamespace(config_relative="portfolio-architect")

    # Model the normal schema-12 all-Gateway coordinator surface used by
    # binary_sensor._source_attributes(). Deliberately do not create local_paths.
    coordinator.source_type = "rest_api"
    coordinator.source_provider = "multi_source"
    coordinator.source_label = "3 sources"
    coordinator.source_count = 3
    coordinator.provider_count = 3
    coordinator.provider_ids = ("comdirect", "trade_republic", "dkb")
    coordinator.provider_summary = "Multi-source portfolio · 3 providers"
    coordinator.provider_summary_de = "Portfolio aus mehreren Quellen · 3 Anbieter"
    coordinator.unavailable_source_count = 0
    coordinator.unavailable_source_ids = ()
    coordinator.unavailable_source_summary = "All configured sources available"
    coordinator.unavailable_source_summary_de = "Alle konfigurierten Quellen verfügbar"
    coordinator.source_conflict_count = 0
    stamp = datetime(2026, 8, 24, 18, 26, 30, tzinfo=timezone.utc)
    coordinator.source_last_changed = stamp
    coordinator.source_last_updated = stamp
    coordinator.data_timestamp = stamp
    coordinator.is_data_fresh = lambda: True
    coordinator.freshness_policy = "evidence_kind_thresholds"
    coordinator.effective_freshness_thresholds = {
        "live_api": 24,
        "imported_statement": 336,
        "csv": 336,
    }
    coordinator.data_fresh_through = stamp
    coordinator.stale_source_ids = ()
    coordinator.stale_source_summary = "No stale sources"
    coordinator.stale_source_summary_de = "Keine veralteten Quellen"
    coordinator.plan_actionable = True
    coordinator.plan_actionability_reason = "actionable"
    coordinator.plan_actionability_detail = "Plan is actionable"
    coordinator.plan_actionability_detail_de = "Plan ist umsetzbar"
    coordinator.source_entity_id = None

    attributes = _load_source_attributes()(coordinator)
    assert attributes["configuration_directory"] == "portfolio-architect"
    assert attributes["provider_ids"] == ["comdirect", "trade_republic", "dkb"]
    assert attributes["data_fresh"] is True
