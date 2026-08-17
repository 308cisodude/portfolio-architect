"""Regression contracts for v1.21.0 execution semantics."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from execution_semantics import (
    PLAN_ACTIONABILITY_ACTIONABLE_NOW,
    PLAN_ACTIONABILITY_NOT_ACTIONABLE,
    PLAN_ACTIONABILITY_NOT_READY,
    PLAN_ACTIONABILITY_OVERDUE,
    PLAN_ACTIONABILITY_SCHEDULED,
    PLAN_ACTIONABILITY_STATES,
    SCHEDULE_RELATION_DUE_TODAY,
    SCHEDULE_RELATION_NOT_CONFIGURED,
    SCHEDULE_RELATION_PAST,
    SCHEDULE_RELATION_UPCOMING,
    derive_plan_actionability,
)



def test_past_scheduled_date_does_not_expire_an_otherwise_actionable_plan() -> None:
    semantics = derive_plan_actionability(
        source_actionable=True,
        execution_state="ready",
        planned_execution_on=date(2026, 8, 7),
        current_date=date(2026, 8, 12),
    )
    assert semantics.state == PLAN_ACTIONABILITY_OVERDUE
    assert semantics.schedule_relation == SCHEDULE_RELATION_PAST
    assert semantics.days_until_scheduled_execution == -5


def test_schedule_timing_and_actionability_are_separate() -> None:
    future = derive_plan_actionability(
        source_actionable=True,
        execution_state="ready",
        planned_execution_on=date(2026, 8, 15),
        current_date=date(2026, 8, 12),
    )
    due = derive_plan_actionability(
        source_actionable=True,
        execution_state="ready",
        planned_execution_on=date(2026, 8, 12),
        current_date=date(2026, 8, 12),
    )
    assert future.state == PLAN_ACTIONABILITY_SCHEDULED
    assert future.schedule_relation == SCHEDULE_RELATION_UPCOMING
    assert future.days_until_scheduled_execution == 3
    assert due.state == PLAN_ACTIONABILITY_ACTIONABLE_NOW
    assert due.schedule_relation == SCHEDULE_RELATION_DUE_TODAY
    assert due.days_until_scheduled_execution == 0


def test_source_trust_and_execution_readiness_override_calendar_timing() -> None:
    source_blocked = derive_plan_actionability(
        source_actionable=False,
        execution_state="ready",
        planned_execution_on=date(2026, 8, 7),
        current_date=date(2026, 8, 12),
    )
    not_ready = derive_plan_actionability(
        source_actionable=True,
        execution_state="waiting_for_reserve",
        planned_execution_on=date(2026, 8, 7),
        current_date=date(2026, 8, 12),
    )
    assert source_blocked.state == PLAN_ACTIONABILITY_NOT_ACTIONABLE
    assert source_blocked.schedule_relation == SCHEDULE_RELATION_PAST
    assert not_ready.state == PLAN_ACTIONABILITY_NOT_READY
    assert not_ready.schedule_relation == SCHEDULE_RELATION_PAST


def test_unscheduled_ready_plan_can_be_actionable_without_inventing_a_date() -> None:
    semantics = derive_plan_actionability(
        source_actionable=True,
        execution_state="ready",
        planned_execution_on=None,
        current_date=date(2026, 8, 12),
    )
    assert semantics.state == PLAN_ACTIONABILITY_ACTIONABLE_NOW
    assert semantics.schedule_relation == SCHEDULE_RELATION_NOT_CONFIGURED
    assert semantics.days_until_scheduled_execution is None


def test_actionability_state_contract_is_bounded() -> None:
    assert PLAN_ACTIONABILITY_STATES == (
        "actionable_now",
        "scheduled",
        "overdue_actionable",
        "not_ready",
        "not_actionable",
    )


def test_native_sensor_exposes_current_actionability_without_renaming_existing_date_entity() -> None:
    source = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    assert "PortfolioPlanActionabilitySensor(coordinator, entry)" in source
    assert '_attr_translation_key = "plan_actionability"' in source
    assert 'return "plan_actionability"' in source
    assert 'object_id = "planned_execution"' in source
    assert '"scheduled_execution_on"' in source
    assert '"evaluated_at"' in source
    assert '"schedule_relation"' in source
    assert '"days_until_scheduled_execution"' in source


def test_translations_make_schedule_and_actionability_explicit() -> None:
    en = json.loads((COMPONENT / "translations" / "en.json").read_text(encoding="utf-8"))
    de = json.loads((COMPONENT / "translations" / "de.json").read_text(encoding="utf-8"))
    assert en["entity"]["sensor"]["planned_execution"]["name"] == "Scheduled execution"
    assert de["entity"]["sensor"]["planned_execution"]["name"] == "Geplante Ausführung"
    assert en["entity"]["sensor"]["plan_actionability"]["state"]["overdue_actionable"] == "Overdue but actionable"
    assert de["entity"]["sensor"]["plan_actionability"]["state"]["overdue_actionable"] == "Überfällig, aber umsetzbar"
    assert en["entity"]["binary_sensor"]["data_fresh"]["state"]["on"] == "Within freshness window"


def test_reference_dashboard_shows_schedule_actionability_and_evaluation_separately() -> None:
    source = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")
    assert source.count("sensor.portfolio_architect_plan_actionability") >= 2
    assert source.count("sensor.portfolio_architect_last_successful_refresh") >= 4
    assert source.count("name: Scheduled execution") == 1
    assert source.count("name: Geplante Ausführung") == 1
    assert source.count("name: Actionability") == 1
    assert source.count("name: Umsetzbarkeit") == 1
    assert not re.search(r"^\s*name: Execution\s*$", source, flags=re.MULTILINE)


def test_reference_dashboard_surfaces_freshness_window_semantics() -> None:
    dashboard = yaml.safe_load((ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8"))
    source = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")
    assert "name: Snapshot freshness" in source
    assert "name: Snapshot-Aktualität" in source
    # The freshness card must show its translated on/off state so LKG can read
    # "Snapshot freshness / Within freshness window" rather than imply live data.
    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)
    cards = [item for item in walk(dashboard) if item.get("entity") == "binary_sensor.portfolio_architect_data_fresh" and item.get("type") == "tile"]
    assert cards
    assert all(item.get("hide_state") is False for item in cards)


def test_v1210_does_not_add_transaction_or_execution_evidence_semantics() -> None:
    source = (COMPONENT / "execution_semantics.py").read_text(encoding="utf-8").lower()
    assert "transaction" not in source
    assert "trade executed" not in source
    assert "order placed" not in source


def test_v1210_version_and_wire_contracts_are_aligned() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    app = yaml.safe_load((ROOT / "home_assistant_app" / "portfolio_architect_gateway" / "config.yaml").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.31.2"
    assert app["version"] == "1.31.2"
    assert 'VERSION: Final = "1.31.2"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert '__version__ = "1.31.2"' in (COMPONENT / "engine" / "__init__.py").read_text(encoding="utf-8")
    assert manifest["version"] == app["version"]
    # Execution semantics are additive Home Assistant entities only.
    assert '"schema_version": 8' in (COMPONENT / "engine" / "calculator.py").read_text(encoding="utf-8")
    gateway_server = (ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "server.py").read_text(encoding="utf-8")
    assert '"health_schema_version": min(version, 6)' in gateway_server
