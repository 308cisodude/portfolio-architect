"""v1.12.1 UI and observability hotfix contracts."""

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


def test_time_derived_attention_entities_refresh_each_minute() -> None:
    sensor = (COMPONENT / "sensor.py").read_text()
    assert "class _MinuteTickEntity:" in sensor
    assert "class PortfolioGatewayRefreshScheduleSensor(\n    _MinuteTickEntity," in sensor
    assert "class PortfolioGatewayAttentionReasonSensor(\n    _MinuteTickEntity," in sensor
    assert "class PortfolioGatewayRecommendedActionSensor(\n    _MinuteTickEntity," in sensor
    assert "REFRESH_SCHEDULE_TICK = timedelta(minutes=1)" in sensor


def test_position_source_provenance_is_a_native_translated_entity() -> None:
    sensor = (COMPONENT / "sensor.py").read_text()
    assert "class PortfolioPositionSourcesSensor" in sensor
    assert 'context=f"{fund_id}:position_sources"' not in sensor  # base class owns context
    assert 'super().__init__(coordinator, entry, fund_id, "position_sources")' in sensor
    assert '"source_summary": _compact_source_summary(contributions)' in sensor
    assert '"source_contributions": contributions' in sensor
    assert '"consolidated_value_eur": position.current_value_eur' in sensor
    assert "PortfolioPositionSourcesSensor(" in sensor

    icons = json.loads((COMPONENT / "icons.json").read_text())
    assert icons["entity"]["sensor"]["position_sources"]["default"] == "mdi:source-branch"
    for language in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text()
        )
        item = translations["entity"]["sensor"]["position_sources"]
        assert item["name"]
        assert "source_summary" in item["state_attributes"]
        assert "source_contributions" in item["state_attributes"]


def test_dashboard_exposes_overlapping_target_position_sources() -> None:
    plan = yaml.safe_load((ROOT / "examples/current-plan/portfolio.yaml").read_text())
    world_id = next(
        item["target_id"]
        for item in plan["portfolio"]["allocation"]
        if item["isin"] == "IE00BJ0KDQ92"
    )
    entity_id = f"sensor.portfolio_architect_{world_id}_position_sources"
    dashboard = yaml.safe_load((ROOT / "dashboard/target-architecture.yaml").read_text())
    cards = [item for item in _walk(dashboard) if isinstance(item, dict)]
    world = next(
        item for item in cards
        if item.get("type") == "tile" and item.get("entity") == entity_id
    )
    assert world["name"] == "MSCI World sources"
    assert world["state_content"] == "source_summary"
    assert world["color"] == "blue"
    source = (ROOT / "dashboard/bilingual-dashboard.yaml").read_text()
    assert entity_id in source
    assert "name: MSCI World sources" in source
    assert "name: Quellen MSCI World" in source
