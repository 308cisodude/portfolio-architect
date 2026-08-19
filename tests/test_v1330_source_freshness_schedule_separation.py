"""v1.35.3 source freshness and plan-schedule separation regressions."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"

_spec = importlib.util.spec_from_file_location(
    "portfolio_architect_freshness_v1330", COMPONENT / "freshness.py"
)
assert _spec is not None and _spec.loader is not None
freshness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(freshness)

NOW = datetime(2026, 8, 18, 8, 30, tzinfo=timezone.utc)
SOURCES = (
    {
        "source_id": "comdirect",
        "provider": "comdirect",
        "label": "Comdirect",
        "generated_at": "2026-08-18T08:20:00+00:00",
    },
    {
        "source_id": "trade_republic",
        "provider": "trade_republic",
        "label": "Trade Republic",
        "generated_at": "2026-08-13T06:11:11+00:00",
    },
    {
        "source_id": "dkb_1",
        "provider": "dkb_csv",
        "label": "DKB CSV",
        "generated_at": "2026-07-31T00:00:00+00:00",
    },
)


def test_upgrade_without_explicit_provider_policy_keeps_legacy_fail_closed_result() -> None:
    rows = freshness.source_freshness_rows(
        SOURCES,
        now=NOW,
        threshold_hours=168,
        threshold_hours_by_kind={},
    )
    assert [item["threshold_hours"] for item in rows] == [168, 168, 168]
    assert tuple(item["source_id"] for item in freshness.stale_rows(rows)) == ("dkb_1",)


def test_explicit_evidence_kind_policy_can_treat_document_sources_differently() -> None:
    rows = freshness.source_freshness_rows(
        SOURCES,
        now=NOW,
        threshold_hours=168,
        threshold_hours_by_kind={
            "live_api": 24,
            "gateway_snapshot": 24,
            "imported_statement": 168,
            "imported_csv": 744,
            "other": 24,
        },
    )
    assert [(item["evidence_kind"], item["threshold_hours"]) for item in rows] == [
        ("live_api", 24),
        ("imported_statement", 168),
        ("imported_csv", 744),
    ]
    assert freshness.stale_rows(rows) == ()


def test_provider_aware_policy_still_fails_closed_per_source() -> None:
    rows = freshness.source_freshness_rows(
        (
            SOURCES[0],
            SOURCES[1],
            {**SOURCES[2], "generated_at": "2026-07-01T00:00:00+00:00"},
        ),
        now=NOW,
        threshold_hours=168,
        threshold_hours_by_kind={
            "live_api": 24,
            "gateway_snapshot": 24,
            "imported_statement": 168,
            "imported_csv": 744,
            "other": 24,
        },
    )
    blockers = freshness.stale_rows(rows)
    assert tuple(item["source_id"] for item in blockers) == ("dkb_1",)
    assert blockers[0]["threshold_hours"] == 744
    assert "limit 31 days" in freshness.stale_summary(blockers)


def _function_source(path: Path, name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"function {name!r} not found")


def test_source_freshness_no_longer_uses_plan_review_schedule_as_freshness_gate() -> None:
    body = _function_source(COMPONENT / "coordinator.py", "is_data_fresh")
    assert "source_freshness_evidence" in body
    assert "plan_review_schedule" not in body
    assert "next_review_on" not in body
    assert 'item.get("within_age_threshold") is True' in body


def test_restore_file_based_plan_preserves_schedule_and_runtime_options() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_PLAN_OVERRIDE_OPTION_KEYS" for target in node.targets)
    )
    assert isinstance(assignment.value, ast.Tuple)
    names = {
        item.id for item in assignment.value.elts if isinstance(item, ast.Name)
    }
    assert names == {
        "CONF_PLAN_OVERRIDE_ENABLED",
        "CONF_PLAN_NAME",
        "CONF_PLAN_BUDGET_AMOUNT",
        "CONF_PLAN_BUDGET_BASIS",
        "CONF_PLAN_INSTRUMENTS",
    }
    for schedule_key in {
        "CONF_PLAN_FREQUENCY",
        "CONF_PLAN_SCHEDULE_ENABLED",
        "CONF_PLAN_EXECUTION_DAYS",
        "CONF_PLAN_EXECUTION_MONTH",
        "CONF_PLAN_EXECUTION_MONTH_OFFSET",
        "CONF_REVIEW_LEAD_DAYS",
    }:
        assert schedule_key not in names
    reset = _function_source(COMPONENT / "config_flow.py", "async_step_reset_plan")
    assert "_PLAN_OVERRIDE_OPTION_KEYS" in reset
    independent = _function_source(COMPONENT / "config_flow.py", "async_step_plan_schedule")
    assert "CONF_PLAN_OVERRIDE_ENABLED" not in independent
    assert "CONF_PLAN_SCHEDULE_ENABLED" in independent
    assert "CONF_PLAN_FREQUENCY" in independent


def test_runtime_flow_exposes_bounded_evidence_kind_thresholds() -> None:
    source = _function_source(COMPONENT / "config_flow.py", "async_step_runtime")
    for key in (
        "CONF_FRESHNESS_LIVE_API_HOURS",
        "CONF_FRESHNESS_STATEMENT_HOURS",
        "CONF_FRESHNESS_CSV_HOURS",
        "CONF_FRESHNESS_OTHER_HOURS",
    ):
        assert key in source
    assert "MAX_DOCUMENT_FRESHNESS_HOURS" in source
    assert "MAX_FRESHNESS_HOURS" in source


def test_translation_contract_explicitly_separates_schedule_from_freshness() -> None:
    en = json.loads((COMPONENT / "translations" / "en.json").read_text(encoding="utf-8"))
    de = json.loads((COMPONENT / "translations" / "de.json").read_text(encoding="utf-8"))
    assert "independently" in en["options"]["step"]["runtime"]["description"]
    assert "unabhängig" in de["options"]["step"]["runtime"]["description"]
    assert "preserved" in en["options"]["step"]["reset_plan"]["description"]
    assert "erhalten" in de["options"]["step"]["reset_plan"]["description"]
    assert set(en["options"]["step"]["runtime"]["data"]) == set(
        de["options"]["step"]["runtime"]["data"]
    )
