"""Regression contracts for v1.26.4 native dashboard date formatting."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
COMPONENT = ROOT / "custom_components" / "portfolio_architect"

NEXT_REFRESH = "sensor.portfolio_architect_gateway_next_refresh"
EXPECTED_NATIVE_DATETIME_FORMAT = {"type": "datetime", "style": "short"}


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _dashboard_documents() -> list[tuple[Path, object]]:
    documents: list[tuple[Path, object]] = []
    for path in sorted(DASHBOARD.rglob("*.yaml")):
        documents.append((path, yaml.safe_load(path.read_text(encoding="utf-8"))))
    return documents


def test_v1264_authoritative_date_sensors_are_preserved_for_v1265() -> None:
    """The failed v1.26.4 Tile workaround must not mutate the data contract."""
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    for entity_class in (
        "PortfolioPlannedExecutionSensor",
        "PortfolioNextPlanReviewSensor",
        "PortfolioLastExceptionDecisionSensor",
        "PortfolioNextExceptionReviewSensor",
        "PortfolioOldestOverdueExceptionReviewSensor",
    ):
        assert entity_class in sensor

def test_refresh_schedule_tiles_keep_native_short_datetime_without_seconds_override() -> None:
    found = 0
    for path, document in _dashboard_documents():
        for card in _walk(document):
            if card.get("type") != "tile" or card.get("entity") != NEXT_REFRESH:
                continue
            found += 1
            assert card.get("time_format") == EXPECTED_NATIVE_DATETIME_FORMAT, path
            # Generic Tile formatting intentionally has no explicit seconds field,
            # format string, template, or locale-specific display attribute.
            assert set(card["time_format"]) == {"type", "style"}, path
    assert found > 0


def test_date_entities_remain_native_home_assistant_date_sensors() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")

    policy_base = sensor.split("class _PortfolioPolicyDateSensor", 1)[1].split(
        "class PortfolioOldestOverdueExceptionReviewSensor", 1
    )[0]
    schedule_base = sensor.split("class _PortfolioPlanScheduleDateSensor", 1)[1].split(
        "class PortfolioPlannedExecutionSensor", 1
    )[0]
    next_review = sensor.split("class PortfolioNextExceptionReviewSensor", 1)[1].split(
        "class PortfolioOverdueExceptionReviewCountSensor", 1
    )[0]

    for block in (policy_base, schedule_base, next_review):
        assert "SensorDeviceClass.DATE" in block
        assert "-> date | None" in block


def test_v1264_adds_no_locale_specific_date_presentation_attribute() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    presentation = (COMPONENT / "presentation.py").read_text(encoding="utf-8")
    combined = sensor + "\n" + presentation
    assert "display_date_de" not in combined
    assert "date_display_de" not in combined
    assert "planned_execution_display" not in combined
    assert "exception_review_display" not in combined
