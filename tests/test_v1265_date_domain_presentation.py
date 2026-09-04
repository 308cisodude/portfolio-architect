"""Regression contracts for v1.26.5 native date-domain presentation."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
DASHBOARD = ROOT / "dashboard"

DATE_KEYS = {
    "planned_execution",
    "next_plan_review",
    "last_exception_decision",
    "next_exception_review",
    "oldest_overdue_exception_review",
}
AUTHORITATIVE_SENSORS = {
    f"sensor.portfolio_architect_{key}" for key in DATE_KEYS
}
PRESENTATION_DATES = {
    f"date.portfolio_architect_{key}" for key in DATE_KEYS
}


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _dashboard_documents() -> list[tuple[Path, object]]:
    return [
        (path, yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted(DASHBOARD.rglob("*.yaml"))
    ]


def test_integration_forwards_native_date_platform() -> None:
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert "Platform.SENSOR" in const
    assert "Platform.BINARY_SENSOR" in const
    assert "Platform.DATE" in const


def test_presentation_platform_is_native_date_and_fail_closed_read_only() -> None:
    source = (COMPONENT / "date.py").read_text(encoding="utf-8")

    assert "from homeassistant.components.date import DateEntity" in source
    assert "CoordinatorEntity[PortfolioArchitectCoordinator], DateEntity" in source
    assert "def native_value(self) -> date | None" in source
    assert "async def async_set_value(self, value: date) -> None" in source
    assert "raise HomeAssistantError(_READ_ONLY_ERROR)" in source
    assert "_date_presentation" in source

    # v1.26.5 must not coerce dates through a fabricated timestamp/noon adapter.
    assert "datetime(" not in source
    assert "datetime.combine" not in source
    assert "timedelta" not in source
    assert "combine(" not in source
    assert "noon" not in source.lower()


def test_original_date_sensors_remain_authoritative_and_unchanged_in_kind() -> None:
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


def test_all_reference_date_tiles_use_date_domain_counterparts_only_for_display() -> None:
    counts: Counter[str] = Counter()
    for path, document in _dashboard_documents():
        for node in _walk(document):
            if node.get("type") == "tile" and node.get("entity") in PRESENTATION_DATES:
                entity = node["entity"]
                counts[entity] += 1
                assert "state_content" not in node, (path, entity)
                assert "time_format" not in node, (path, entity)
                authoritative = entity.replace("date.", "sensor.", 1)
                assert node.get("tap_action") == {
                    "action": "more-info",
                    "entity": authoritative,
                }, (path, entity)

            # Presentation entities must never become state/availability conditions.
            if node.get("condition") == "state":
                assert node.get("entity") not in PRESENTATION_DATES, path

    # v1.63.0 replaced the duplicated dashboard authoring tree with one shared
    # structural source plus generated locale projections. Across the tracked
    # dashboard tree, each presentation date therefore appears once in shared
    # source, once in each single-language projection, twice in the generated
    # bilingual projection, and twice in its compatibility copy.
    assert counts == Counter({entity: 7 for entity in PRESENTATION_DATES})


def test_reference_dashboards_do_not_render_authoritative_date_sensors_directly() -> None:
    for path, document in _dashboard_documents():
        for node in _walk(document):
            if node.get("type") == "tile":
                assert node.get("entity") not in AUTHORITATIVE_SENSORS, path


def test_date_platform_has_localized_names_and_icons() -> None:
    icons = json.loads((COMPONENT / "icons.json").read_text(encoding="utf-8"))
    assert set(DATE_KEYS) <= set(icons["entity"]["date"])

    for language in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(
                encoding="utf-8"
            )
        )
        date_translations = translations["entity"]["date"]
        assert set(DATE_KEYS) <= set(date_translations)
        for key in DATE_KEYS:
            assert date_translations[key]["name"].strip()
