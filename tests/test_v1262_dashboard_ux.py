from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from presentation import (  # noqa: E402
    display_binary_state_de,
    display_eur_de,
    display_state_de,
    unavailable_source_summary,
)


def _tile_cards(value):
    if isinstance(value, dict):
        if value.get("type") == "tile" and isinstance(value.get("entity"), str):
            yield value
        for child in value.values():
            yield from _tile_cards(child)
    elif isinstance(value, list):
        for child in value:
            yield from _tile_cards(child)


def test_german_presentation_values_are_dashboard_language_owned() -> None:
    assert display_state_de("plan_frequency", "monthly") == "Monatlich"
    assert display_state_de("execution_policy", "efficiency_first") == "Effizienz zuerst"
    assert display_state_de("plan_actionability", "not_actionable") == "Nicht umsetzbar"
    assert display_state_de("gateway_status", "degraded") == "Eingeschränkt"
    assert display_state_de("gateway_operating_mode", "last_known_good") == "Letzter gültiger Stand"
    assert display_state_de("gateway_last_refresh_trigger", "scheduled") == "Geplant"
    assert (
        display_state_de("gateway_attention_reason", "supplemental_source_unavailable")
        == "Zusätzliche Quelle nicht verfügbar"
    )
    assert display_state_de("gateway_recommended_action", "check_connectivity") == "Verbindung prüfen"
    assert display_binary_state_de("data_fresh", True) == "Im Aktualitätsfenster"
    assert display_eur_de("8100") == "8.100,00 €"
    assert display_eur_de(None, available=False) == "Nicht verfügbar"


def test_german_reference_dashboard_uses_explicit_german_presentation_attributes() -> None:
    document = yaml.safe_load(
        (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")
    )
    german = next(view for view in document["views"] if view["title"] == "DE")
    cards = list(_tile_cards(german))

    required = {
        "sensor.portfolio_architect_plan_change",
        "sensor.portfolio_architect_plan_budget",
        "sensor.portfolio_architect_plan_frequency",
        "sensor.portfolio_architect_monthly_contribution",
        "sensor.portfolio_architect_plan_actionability",
        "sensor.portfolio_architect_execution_policy",
        "binary_sensor.portfolio_architect_data_fresh",
        "sensor.portfolio_architect_gateway_status",
        "sensor.portfolio_architect_gateway_last_refresh",
        "sensor.portfolio_architect_gateway_operating_mode",
        "sensor.portfolio_architect_gateway_next_refresh",
        "sensor.portfolio_architect_gateway_refresh_schedule",
        "sensor.portfolio_architect_gateway_last_refresh_trigger",
        "sensor.portfolio_architect_gateway_attention_reason",
        "sensor.portfolio_architect_gateway_recommended_action",
        "sensor.portfolio_architect_gateway_last_refresh_failure",
        "sensor.portfolio_architect_gateway_snapshot_generated",
    }
    by_entity: dict[str, list[dict]] = {}
    for card in cards:
        by_entity.setdefault(card["entity"], []).append(card)
    missing = required - by_entity.keys()
    assert not missing
    for entity in required:
        assert any(
            card.get("state_content") == "display_state_de"
            for card in by_entity[entity]
        )

    last_eval = by_entity["sensor.portfolio_architect_last_successful_refresh"]
    assert any(card.get("state_content") == "display_state_de" for card in last_eval)
    assert any(
        card.get("state_content") == ["display_state_de", "engine_version"]
        for card in last_eval
    )


def test_source_unavailable_tiles_name_the_failed_sources_without_raw_state() -> None:
    document = yaml.safe_load(
        (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")
    )
    english = next(view for view in document["views"] if view["title"] == "EN")
    german = next(view for view in document["views"] if view["title"] == "DE")
    en = [c for c in _tile_cards(english) if c.get("name") == "Source unavailable"]
    de = [c for c in _tile_cards(german) if c.get("name") == "Quelle fehlt"]
    assert len(en) == 1 and en[0]["state_content"] == "unavailable_source_summary"
    assert len(de) == 1 and de[0]["state_content"] == "unavailable_source_summary_de"
    assert not en[0].get("hide_state")
    assert not de[0].get("hide_state")


def test_unavailable_source_summary_is_bounded_and_privacy_safe() -> None:
    source_ids = ("gateway:trade_republic", "gateway:dkb")
    assert (
        unavailable_source_summary(source_ids, german=False)
        == "Trade Republic Gateway · DKB Gateway"
    )
    assert (
        unavailable_source_summary(source_ids, german=True)
        == "Trade-Republic-Gateway · DKB-Gateway"
    )
    serialized = repr(
        {
            "ids": source_ids,
            "summary": unavailable_source_summary(source_ids, german=False),
        }
    )
    assert "http" not in serialized.lower()
    assert "token" not in serialized.lower()
    assert "/config" not in serialized


def test_attention_reason_none_bug_is_closed_by_declared_state_and_translation() -> None:
    sensor_source = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    coordinator_source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    assert 'return "supplemental_source_unavailable"' in coordinator_source
    assert '"supplemental_source_unavailable"' in sensor_source
    for language, expected in (
        ("en", "Supplemental source unavailable"),
        ("de", "Zusätzliche Quelle nicht verfügbar"),
    ):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(
                encoding="utf-8"
            )
        )
        assert (
            translations["entity"]["sensor"]["gateway_attention_reason"]["state"]
            ["supplemental_source_unavailable"]
            == expected
        )


def test_source_health_entity_exposes_failed_source_metadata_without_endpoint_or_token() -> None:
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    diagnostics = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    for token in (
        '"unavailable_source_count"',
        '"unavailable_source_ids"',
        '"unavailable_source_summary"',
        '"unavailable_source_summary_de"',
    ):
        assert token in binary
    assert '"unavailable_sources"' in diagnostics
    assert "unavailable_source_ids" in coordinator
    # Public labels are derived from bounded provider/source IDs, never the private endpoint/token.
    presentation = (COMPONENT / "presentation.py").read_text(encoding="utf-8")
    summary_function = presentation.split("def unavailable_source_label", 1)[1]
    assert "endpoint_url" not in summary_function
    assert "api_token" not in summary_function


def test_multi_gateway_failure_collection_does_not_stop_at_first_failed_provider() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    function = coordinator.split(
        "async def _async_fetch_supplemental_rest_snapshots", 1
    )[1].split("\n\nclass SupplementalPortfolioSourceError", 1)[0]
    assert "errors: dict[str, str] = {}" in function
    assert 'errors[config.provider_id] = "authentication_error"' in function
    assert 'errors[config.provider_id] = "transport_error"' in function
    assert 'errors[config.provider_id] = "identity_error"' in function
    assert "return tuple(snapshots), health_by_provider, errors" in function
    # The per-provider branches continue collecting instead of raising on the first outage.
    assert "continue" in function
