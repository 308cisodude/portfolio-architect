"""v1.49.0 live source-summary acquisition-mode propagation regressions."""

from __future__ import annotations

import ast
import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.aggregation import PortfolioSourceSnapshot, aggregate_sources  # noqa: E402
from engine.models import Position  # noqa: E402

NOW = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)


def _freshness_module():
    path = COMPONENT / "freshness.py"
    spec = importlib.util.spec_from_file_location("portfolio_architect_v1482_freshness", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _StripAnnotations(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef):  # noqa: N802
        node = copy.deepcopy(node)
        node.returns = None
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            arg.annotation = None
        if node.args.vararg is not None:
            node.args.vararg.annotation = None
        if node.args.kwarg is not None:
            node.args.kwarg.annotation = None
        return self.generic_visit(node)


def _extract_function(name: str, *, from_class: bool = False):
    source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    candidates: list[ast.FunctionDef] = []
    if from_class:
        for item in tree.body:
            if isinstance(item, ast.ClassDef) and item.name == "PortfolioArchitectCoordinator":
                candidates.extend(
                    child
                    for child in item.body
                    if isinstance(child, ast.FunctionDef) and child.name == name
                )
    else:
        candidates.extend(
            item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == name
        )
    assert len(candidates) == 1
    function = _StripAnnotations().visit(candidates[0])
    ast.fix_missing_locations(function)
    freshness = _freshness_module()
    namespace = {
        "annotate_source_acquisition_modes": freshness.annotate_source_acquisition_modes,
        "datetime": datetime,
        "timezone": timezone,
    }
    module = ast.Module(body=[function], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, "<coordinator-extract>", "exec"), namespace)
    return namespace[name]


def _position(isin: str, value: str, name: str) -> Position:
    return Position(
        wkn="",
        isin=isin,
        name=name,
        instrument_type="etf",
        source_type="ETF",
        value_eur=Decimal(value),
    )


def _three_provider_aggregation():
    return aggregate_sources(
        (
            PortfolioSourceSnapshot(
                "comdirect",
                "comdirect",
                "Comdirect",
                NOW,
                {"IE0000000001": _position("IE0000000001", "100", "Live")},
            ),
            PortfolioSourceSnapshot(
                "trade_republic",
                "trade_republic",
                "Trade Republic",
                NOW,
                {"IE0000000002": _position("IE0000000002", "200", "PDF")},
            ),
            PortfolioSourceSnapshot(
                "dkb",
                "dkb",
                "DKB",
                NOW,
                {"IE0000000003": _position("IE0000000003", "300", "CSV")},
            ),
        )
    )


def test_live_apply_aggregation_retains_schema7_modes_and_drives_freshness() -> None:
    freshness = _freshness_module()
    apply_aggregation = _extract_function("_apply_aggregation", from_class=True)
    coordinator = SimpleNamespace()
    aggregation = _three_provider_aggregation()

    apply_aggregation(
        coordinator,
        aggregation,
        acquisition_modes={
            "comdirect": "live_api",
            "trade_republic": "pdf",
            "dkb": "csv",
        },
    )

    summaries = {item["provider"]: item for item in coordinator.source_summaries}
    assert summaries["comdirect"]["acquisition_mode"] == "live_api"
    assert summaries["trade_republic"]["acquisition_mode"] == "pdf"
    assert summaries["dkb"]["acquisition_mode"] == "csv"

    rows = freshness.source_freshness_rows(
        coordinator.source_summaries,
        now=NOW + timedelta(hours=33, minutes=30),
        threshold_hours=24,
        threshold_hours_by_kind=freshness.default_freshness_thresholds("monthly"),
    )
    by_provider = {item["provider"]: item for item in rows}
    assert by_provider["comdirect"]["evidence_kind"] == "live_api"
    assert by_provider["comdirect"]["threshold_hours"] == 24
    assert by_provider["comdirect"]["within_age_threshold"] is False
    assert by_provider["trade_republic"]["evidence_kind"] == "imported_statement"
    assert by_provider["trade_republic"]["threshold_hours"] == 336
    assert by_provider["dkb"]["evidence_kind"] == "csv"
    assert by_provider["dkb"]["threshold_hours"] == 336
    assert by_provider["dkb"]["within_age_threshold"] is True


def test_live_and_lkg_source_summaries_use_the_same_acquisition_annotations() -> None:
    aggregation = _three_provider_aggregation()
    modes = {"comdirect": "live_api", "trade_republic": "pdf", "dkb": "csv"}
    apply_aggregation = _extract_function("_apply_aggregation", from_class=True)
    aggregation_metadata = _extract_function("_aggregation_metadata")
    restore = _extract_function("_restore_source_metadata_from_payload", from_class=True)

    live = SimpleNamespace()
    apply_aggregation(live, aggregation, acquisition_modes=modes)
    metadata = aggregation_metadata(aggregation, modes)
    assert tuple(metadata["source_summaries"]) == live.source_summaries

    restored = SimpleNamespace(supplemental_rest_sources=[])
    restore(
        restored,
        {
            "summary": {
                **metadata,
                "oldest_source_generated_at": aggregation.oldest_generated_at.isoformat(),
                "newest_source_generated_at": aggregation.newest_generated_at.isoformat(),
            }
        },
    )
    assert restored.source_summaries == live.source_summaries
    assert {item["provider"]: item["acquisition_mode"] for item in restored.source_summaries} == modes


def test_mode_refresh_can_clear_a_stale_static_annotation_fail_closed() -> None:
    freshness = _freshness_module()
    summary = ({
        "source_id": "dkb",
        "provider": "dkb",
        "label": "DKB",
        "acquisition_mode": "csv",
        "generated_at": NOW.isoformat(),
    },)
    refreshed = freshness.annotate_source_acquisition_modes(summary, {"dkb": None})
    assert "acquisition_mode" not in refreshed[0]
    row = freshness.source_freshness_rows(
        refreshed,
        now=NOW + timedelta(hours=25),
        threshold_hours=24,
        threshold_hours_by_kind=freshness.default_freshness_thresholds("monthly"),
    )[0]
    assert row["evidence_kind"] == "gateway_snapshot"
    assert row["threshold_hours"] == 24
    assert row["within_age_threshold"] is False


def test_not_modified_refresh_reannotates_existing_source_summary() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    reuse_block = coordinator.split("if reuse_existing_data:", 1)[1].split("try:", 1)[0]
    assert "self.source_summaries = annotate_source_acquisition_modes(" in reuse_block
    assert "self.gateway_health.acquisition_mode" in reuse_block
    assert 'else "unknown"' in reuse_block
