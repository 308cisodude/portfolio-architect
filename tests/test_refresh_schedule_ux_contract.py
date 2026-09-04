"""v1.12.1 newcomer-safe refresh schedule contracts."""

from pathlib import Path

import json
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_refresh_schedule_sensor_is_time_derived_and_translated() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    assert "PortfolioGatewayRefreshScheduleSensor" in sensor
    assert 'context="gateway_refresh_schedule"' in sensor
    assert '_attr_options = ["scheduled", "due_now", "overdue", "refreshing"]' in sensor
    assert "async_track_time_interval" in sensor
    assert "REFRESH_SCHEDULE_TICK = timedelta(minutes=1)" in sensor
    assert "gateway_refresh_grace_seconds" in coordinator
    assert '"scheduled_refresh_time"' in sensor

    for language in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text()
        )
        item = translations["entity"]["sensor"]["gateway_refresh_schedule"]
        assert set(item["state"]) == {"scheduled", "due_now", "overdue", "refreshing"}
        assert "scheduled_refresh_time" in item["state_attributes"]


def test_diagnostic_timestamp_no_longer_claims_to_be_next() -> None:
    en = json.loads((COMPONENT / "translations/en.json").read_text())
    de = json.loads((COMPONENT / "translations/de.json").read_text())
    assert en["entity"]["sensor"]["gateway_next_refresh"]["name"] == "Scheduled refresh time"
    assert de["entity"]["sensor"]["gateway_next_refresh"]["name"] == "Geplanter Aktualisierungszeitpunkt"


def test_dashboard_uses_state_specific_tiles_with_compact_timestamp_state() -> None:
    runtime = yaml.safe_load((ROOT / "dashboard/generated/portfolio-architect-dashboard-en.yaml").read_text())
    conditionals = [
        card for card in _walk(runtime)
        if isinstance(card, dict) and card.get("type") == "conditional"
    ]
    schedule_conditionals = [
        item for item in conditionals
        if any(
            condition.get("entity")
            == "sensor.portfolio_architect_gateway_refresh_schedule"
            for condition in item.get("conditions", [])
        )
    ]
    assert len(schedule_conditionals) == 4
    by_state = {
        next(
            condition["state"]
            for condition in item["conditions"]
            if condition.get("entity")
            == "sensor.portfolio_architect_gateway_refresh_schedule"
        ): item["card"]
        for item in schedule_conditionals
    }
    assert set(by_state) == {"scheduled", "due_now", "overdue", "refreshing"}
    for state in ("scheduled", "due_now", "overdue"):
        card = by_state[state]
        assert card["entity"] == "sensor.portfolio_architect_gateway_next_refresh"
        assert card["state_content"] == "state"
        assert card["time_format"] == {"type": "datetime", "style": "short"}
    assert by_state["refreshing"]["entity"] == (
        "sensor.portfolio_architect_gateway_refresh_schedule"
    )

    source = (ROOT / "dashboard/bilingual-dashboard.yaml").read_text()
    assert "name: Refresh scheduled" in source
    assert "name: Refresh due" in source
    assert "name: Refresh overdue" in source
    assert "name: Abruf geplant" in source
    assert "name: Abruf fällig" in source
    assert "name: Abruf überfällig" in source
    assert "name: Next live refresh" not in source
    assert "name: Nächster Live-Abruf" not in source


def test_review_schedule_uses_latest_evaluation_contract() -> None:
    source = (COMPONENT / "coordinator.py").read_text()
    start = source.index("    def plan_review_schedule")
    end = source.index("    def is_plan_review_due", start)
    body = source[start:end]
    assert "timestamp = self.data_timestamp" in body
    assert "oldest_source_generated_at" not in body
