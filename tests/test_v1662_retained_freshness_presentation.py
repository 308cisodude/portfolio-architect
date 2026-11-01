"""A retained calculation must not blame a newly refreshed Gateway source."""

from pathlib import Path

import pytest
import yaml

jinja2 = pytest.importorskip("jinja2")

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("locale", "missing_label", "retained_heading", "live_heading"),
    (
        (
            "en",
            "DKB Gateway",
            "Dates in the retained calculation (not current Gateway observations)",
            "Authoritative evidence to refresh",
        ),
        (
            "de",
            "DKB-Gateway",
            "Daten der letzten akzeptierten Berechnung (keine aktuellen Gateway-Beobachtungen)",
            "Maßgebliche Nachweise aktualisieren",
        ),
    ),
)
def test_retained_and_live_blockers_are_distinct(
    locale: str, missing_label: str, retained_heading: str, live_heading: str
) -> None:
    catalog = yaml.safe_load(
        (ROOT / "dashboard/src/i18n" / f"{locale}.yaml").read_text(encoding="utf-8")
    )
    template = jinja2.Environment(autoescape=False).from_string(
        catalog["strings"]["plan_source_blocker_content"]
    )
    old_rows = [
        {
            "label": "Trade Republic",
            "evidence_kind": "imported_statement",
            "generated_at": "2026-10-17T12:31:46+00:00",
            "threshold_hours": 336,
            "within_age_threshold": False,
        },
        {
            "label": "DKB",
            "evidence_kind": "fints",
            "generated_at": "2026-10-17T12:40:53+00:00",
            "threshold_hours": 336,
            "within_age_threshold": False,
        },
    ]

    def state_attr(entity: str, attribute: str):
        if entity == "binary_sensor.portfolio_architect_data_fresh":
            return old_rows if attribute == "source_freshness" else None
        if entity == "binary_sensor.portfolio_architect_source_healthy":
            return missing_label if attribute.startswith("unavailable_source_summary") else None
        if entity == "sensor.portfolio_architect_plan_actionability":
            return "Trade Republic and DKB appear stale" if attribute.startswith("plan_actionability_detail") else None
        return None

    retained = template.render(
        is_state=lambda entity, state: entity == "sensor.portfolio_architect_gateway_operating_mode" and state == "last_known_good",
        state_attr=state_attr,
    )
    assert missing_label in retained
    assert retained_heading in retained
    assert "2026-10-17T12:31:46+00:00" in retained
    assert live_heading not in retained
    assert "Trade Republic and DKB appear stale" not in retained

    live = template.render(is_state=lambda _entity, _state: False, state_attr=state_attr)
    assert live_heading in live
    assert retained_heading not in live
    assert "Trade Republic and DKB appear stale" in live
