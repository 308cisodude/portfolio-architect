"""v1.18.1 plan-delta and decision-trace contracts."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from decision_trace import (  # noqa: E402
    DecisionTraceError,
    EvaluationHistory,
    MATERIAL_DRIFT_DELTA_PP,
    MATERIAL_MONEY_DELTA_EUR,
    advance_history,
    build_evaluation_snapshot,
    compare_history,
)
from engine.calculator import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.importers import CsvSourceConfig, PROVIDER_COMDIRECT, read_positions  # noqa: E402
from model import parse_portfolio_data  # noqa: E402


def _data():
    positions = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv",
        CsvSourceConfig(provider=PROVIDER_COMDIRECT),
    )
    payload = calculate_portfolio_payload_from_positions(
        positions,
        ROOT / "examples" / "current-plan",
        evaluated_at=datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc),
        source_provider=PROVIDER_COMDIRECT,
        source_label="Comdirect CSV",
    )
    return parse_portfolio_data(
        payload["recommendations"],
        payload["summary"],
        payload["policy_findings"],
        payload["holdings"],
    )


def _snapshot(data, when):
    return build_evaluation_snapshot(
        data,
        evaluated_at=when,
        source_provider=PROVIDER_COMDIRECT,
        source_count=1,
        source_conflict_count=0,
    )


def test_first_evaluation_establishes_a_bounded_baseline() -> None:
    current = _snapshot(_data(), datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc))
    history, changed = advance_history(EvaluationHistory(), current)
    delta = compare_history(history)
    assert changed is True
    assert delta is not None
    assert delta.state == "baseline_established"
    assert delta.attributes["position_changes"] == []
    assert len(history.to_dict()["current"]["positions"]) == 7


def test_identical_decision_content_at_a_new_evaluation_is_unchanged() -> None:
    data = _data()
    first = _snapshot(data, datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc))
    second = _snapshot(data, datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc))
    history, _ = advance_history(EvaluationHistory(), first)
    history, changed = advance_history(history, second)
    delta = compare_history(history)
    assert changed is True  # a new evaluated_at is a distinct validated evaluation
    assert delta is not None and delta.state == "unchanged"
    assert delta.attributes["change_categories"] == []


def test_position_entering_corridor_and_losing_purchase_is_traced() -> None:
    data = _data()
    previous = _snapshot(data, datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc))
    position = data.positions["world_small_cap"]
    changed_position = replace(
        position,
        allocation_status="on_target",
        deviation_pp=-0.5,
        proposed_buy_eur=0.0,
        recommendation_reason="no_purchase_for_on_target",
    )
    current_data = replace(
        data,
        positions={**data.positions, "world_small_cap": changed_position},
    )
    current = _snapshot(
        current_data, datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)
    )
    delta = compare_history(EvaluationHistory(previous=previous, current=current))
    assert delta is not None and delta.state == "multiple_changes"
    change = delta.attributes["position_changes"][0]
    assert change["fund_id"] == "world_small_cap"
    assert change["categories"] == ["allocation", "recommendation"]
    assert "entered_target_corridor" in change["reason_codes"]
    assert "proposed_purchase_removed" in change["reason_codes"]
    assert change["previous_proposed_buy_eur"] == 350.0
    assert change["current_proposed_buy_eur"] == 0.0


def test_subthreshold_noise_is_not_reported_as_material_change() -> None:
    data = _data()
    previous = _snapshot(data, datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc))
    position = data.positions["world_small_cap"]
    changed_position = replace(
        position,
        deviation_pp=position.deviation_pp + MATERIAL_DRIFT_DELTA_PP / 2,
        proposed_buy_eur=position.proposed_buy_eur + MATERIAL_MONEY_DELTA_EUR / 2,
    )
    current_data = replace(
        data,
        positions={**data.positions, "world_small_cap": changed_position},
    )
    current = _snapshot(
        current_data, datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)
    )
    delta = compare_history(EvaluationHistory(previous=previous, current=current))
    assert delta is not None and delta.state == "unchanged"


def test_execution_policy_and_reserve_transition_is_distinct() -> None:
    data = _data()
    previous = _snapshot(data, datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc))
    changed_plan = replace(
        data.monthly_plan,
        execution_state="waiting_for_reserve",
        reserve_source="gateway_balance",
        available_reserve_eur=1.46,
        additional_investment_cash_required_eur=18.54,
    )
    current = _snapshot(
        replace(data, monthly_plan=changed_plan),
        datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc),
    )
    delta = compare_history(EvaluationHistory(previous=previous, current=current))
    assert delta is not None and delta.state == "execution_state_changed"
    assert delta.attributes["execution_change"]["current_state"] == "waiting_for_reserve"


def test_policy_finding_changes_are_keyed_without_free_form_messages() -> None:
    data = _data()
    previous = _snapshot(data, datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc))
    changed_policy = replace(
        data.policy,
        status="compliant",
        errors=0,
        warnings=0,
        opportunities=0,
        accepted_exceptions=0,
        findings={},
    )
    current = _snapshot(
        replace(data, policy=changed_policy),
        datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc),
    )
    delta = compare_history(EvaluationHistory(previous=previous, current=current))
    assert delta is not None and delta.state == "policy_changed"
    assert "removed_findings" in delta.attributes["policy_change"]
    assert "message" not in json.dumps(delta.attributes)


def test_history_round_trip_is_strict_and_only_contains_two_evaluations() -> None:
    data = _data()
    first = _snapshot(data, datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc))
    second = _snapshot(data, datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc))
    history = EvaluationHistory(previous=first, current=second)
    restored = EvaluationHistory.from_dict(history.to_dict())
    assert restored == history
    malformed = history.to_dict()
    malformed["unexpected"] = True
    with pytest.raises(DecisionTraceError):
        EvaluationHistory.from_dict(malformed)


def test_home_assistant_contract_exposes_one_enum_and_skips_degraded_replays() -> None:
    sensor = (COMPONENT / "sensor.py").read_text()
    coordinator = (COMPONENT / "coordinator.py").read_text()
    setup = (COMPONENT / "__init__.py").read_text()
    assert "class PortfolioPlanChangeSensor" in sensor
    assert '_attr_translation_key = "plan_change"' in sensor
    assert '_unrecorded_attributes = frozenset({MATCH_ALL})' in sensor
    assert "if not self._using_home_assistant_last_known_good" in coordinator
    assert "await coordinator.async_restore_decision_trace()" in setup


def test_translations_and_dashboard_are_bilingual_and_hidden_when_unchanged() -> None:
    en = json.loads((COMPONENT / "translations" / "en.json").read_text())
    de = json.loads((COMPONENT / "translations" / "de.json").read_text())
    for language in (en, de):
        states = language["entity"]["sensor"]["plan_change"]["state"]
        assert set(states) == {
            "baseline_established",
            "unchanged",
            "allocation_changed",
            "recommendation_changed",
            "execution_state_changed",
            "policy_changed",
            "source_changed",
            "multiple_changes",
        }
    dashboard = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text()
    assert dashboard.count("sensor.portfolio_architect_plan_change") == 8
    assert dashboard.count("state_not: unchanged") == 2
    assert "Changes since previous evaluation" in dashboard
    assert "Änderungen seit letzter Auswertung" in dashboard


def test_storage_and_diagnostics_keep_the_trace_private_and_integrity_checked() -> None:
    store = (COMPONENT / "decision_trace_store.py").read_text()
    diagnostics = (COMPONENT / "diagnostics.py").read_text()
    assert 'private=True' in store
    assert 'atomic_writes=True' in store
    assert 'history_sha256' in store
    assert '_history_sha256(raw["history"])' in store
    assert '"decision_trace"' in diagnostics
    assert 'changed_fund_ids' in diagnostics
    assert '"position_changes":' not in diagnostics
    assert 'proposed_buy_delta_eur' not in diagnostics


def test_v1180_metadata_and_compatibility_contracts_are_aligned() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["version"] == "1.20.0"
    assert 'VERSION: Final = "1.20.0"' in (COMPONENT / "const.py").read_text()
    assert '__version__ = "1.20.0"' in (COMPONENT / "engine" / "__init__.py").read_text()
    release_notes = (ROOT / "docs" / "RELEASE-NOTES.md").read_text()
    assert "payload schema 8" in release_notes.lower()
    assert "REST schema 1" in release_notes
    assert "Gateway health schema 5" in release_notes
    assert "Trade Republic" not in release_notes


def test_persisted_trace_rejects_type_confusion_and_duplicate_keys() -> None:
    data = _data()
    snapshot = _snapshot(data, datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc))

    malformed_bool = EvaluationHistory(current=snapshot).to_dict()
    malformed_bool["current"]["positions"][0]["deferred"] = "false"
    with pytest.raises(DecisionTraceError):
        EvaluationHistory.from_dict(malformed_bool)

    duplicate_finding = EvaluationHistory(current=snapshot).to_dict()
    findings = duplicate_finding["current"]["policy"]["active_findings"]
    if findings:
        findings.append(list(findings[0]))
        findings.sort()
        with pytest.raises(DecisionTraceError):
            EvaluationHistory.from_dict(duplicate_finding)
