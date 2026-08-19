"""v1.35.1 scheduling-anchor hotfix regressions."""

from __future__ import annotations

import ast
from datetime import date, datetime, timezone
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"

_spec = importlib.util.spec_from_file_location(
    "portfolio_architect_schedule_v1331", COMPONENT / "schedule.py"
)
assert _spec is not None and _spec.loader is not None
schedule_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = schedule_module
_spec.loader.exec_module(schedule_module)


def _function_source(path: Path, name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"function {name!r} not found")


def test_live_august_topology_anchors_schedule_to_evaluation_not_oldest_source() -> None:
    """Reproduce the v1.35.1 live failure without making source freshness part of scheduling."""
    evaluation = datetime(2026, 8, 18, 10, 18, tzinfo=timezone.utc)
    old_dkb_csv = datetime(2026, 7, 31, 0, 0, tzinfo=timezone.utc)
    config = schedule_module.validate_schedule_config("monthly", [7])

    corrected = schedule_module.calculate_plan_review_schedule(
        evaluation.date(), config, 2
    )
    stale_anchor = schedule_module.calculate_plan_review_schedule(
        old_dkb_csv.date(), config, 2
    )

    assert corrected.planned_execution_on == date(2026, 9, 7)
    assert corrected.next_review_on == date(2026, 10, 5)
    assert stale_anchor.planned_execution_on == date(2026, 8, 7)
    assert stale_anchor.next_review_on == date(2026, 9, 5)


def test_coordinator_schedule_uses_evaluation_timestamp_only() -> None:
    body = _function_source(COMPONENT / "coordinator.py", "plan_review_schedule")
    assert "timestamp = self.data_timestamp" in body
    assert "oldest_source_generated_at" not in body
    assert "calculate_plan_review_schedule" in body


def test_source_freshness_remains_source_timestamp_based_and_separate() -> None:
    freshness = _function_source(COMPONENT / "coordinator.py", "source_freshness_evidence")
    schedule = _function_source(COMPONENT / "coordinator.py", "plan_review_schedule")
    assert "source_summaries" in freshness
    assert "source_freshness_rows" in freshness
    assert "oldest_source_generated_at" not in schedule
    assert "freshness" not in schedule.lower()


def test_release_contract_keeps_v1330_freshness_policy_and_changes_only_schedule_anchor() -> None:
    notes = (ROOT / "docs" / "RELEASE-NOTES.md").read_text(encoding="utf-8")
    assert "v1.33.0 source-freshness and plan-schedule separation" in notes
    assert "latest valid Portfolio Architect evaluation" in notes
    assert "does not change any configured freshness threshold" in notes
    assert "No trading, order, transfer, payment, or transaction-history capability" in notes
