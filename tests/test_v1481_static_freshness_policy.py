"""v1.51.1 cadence-aware static evidence freshness regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def _freshness_module():
    path = COMPONENT / "freshness.py"
    spec = importlib.util.spec_from_file_location("portfolio_architect_v1481_freshness", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unconfigured_static_defaults_follow_plan_cadence() -> None:
    freshness = _freshness_module()
    monthly = freshness.default_freshness_thresholds("monthly")
    weekly = freshness.default_freshness_thresholds("weekly")
    quarterly = freshness.default_freshness_thresholds("quarterly")
    yearly = freshness.default_freshness_thresholds("yearly")

    assert monthly == {
        "live_api": 24,
        "gateway_snapshot": 24,
        "imported_statement": 14 * 24,
        "imported_csv": 14 * 24,
        "csv": 14 * 24,
        "other": 24,
    }
    assert weekly["live_api"] == 24
    assert weekly["gateway_snapshot"] == 24
    assert weekly["imported_statement"] == 5 * 24
    assert weekly["imported_csv"] == 5 * 24
    assert weekly["csv"] == 5 * 24
    assert quarterly["csv"] == 14 * 24
    assert yearly["imported_statement"] == 14 * 24


def test_explicit_legacy_global_threshold_is_not_silently_weakened() -> None:
    freshness = _freshness_module()
    thresholds = freshness.default_freshness_thresholds(
        "weekly", legacy_threshold_hours=168, preserve_legacy_global=True
    )
    assert set(thresholds.values()) == {168}


def test_health_schema_7_acquisition_mode_drives_evidence_kind() -> None:
    freshness = _freshness_module()
    assert freshness.evidence_kind("comdirect", "live_api") == "live_api"
    assert freshness.evidence_kind("comdirect", "csv") == "csv"
    assert freshness.evidence_kind("dkb", "csv") == "csv"
    assert freshness.evidence_kind("trade_republic", "pdf") == "imported_statement"
    # Older health schemas do not expose acquisition_mode and stay conservative.
    assert freshness.evidence_kind("dkb", None) == "gateway_snapshot"

    assert freshness.cash_evidence_kind("comdirect", "csv") == "csv"
    assert freshness.cash_evidence_kind("dkb", "csv") == "csv"
    assert freshness.cash_evidence_kind("trade_republic", "pdf") == "imported_statement"


def test_monthly_static_dkb_is_fresh_at_33_point_5_hours_while_legacy_unknown_is_not() -> None:
    freshness = _freshness_module()
    now = datetime(2026, 8, 24, 9, 30, tzinfo=timezone.utc)
    generated = now - timedelta(hours=33, minutes=30)
    defaults = freshness.default_freshness_thresholds("monthly")

    static_rows = freshness.source_freshness_rows(
        ({
            "source_id": "dkb",
            "provider": "dkb",
            "label": "DKB",
            "acquisition_mode": "csv",
            "generated_at": generated.isoformat(),
        },),
        now=now,
        threshold_hours=24,
        threshold_hours_by_kind=defaults,
    )
    assert static_rows[0]["evidence_kind"] == "csv"
    assert static_rows[0]["threshold_hours"] == 336
    assert static_rows[0]["within_age_threshold"] is True

    legacy_rows = freshness.source_freshness_rows(
        ({
            "source_id": "dkb",
            "provider": "dkb",
            "label": "DKB",
            "generated_at": generated.isoformat(),
        },),
        now=now,
        threshold_hours=24,
        threshold_hours_by_kind=defaults,
    )
    assert legacy_rows[0]["evidence_kind"] == "gateway_snapshot"
    assert legacy_rows[0]["threshold_hours"] == 24
    assert legacy_rows[0]["within_age_threshold"] is False


def test_weekly_static_window_is_five_days() -> None:
    freshness = _freshness_module()
    now = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)
    defaults = freshness.default_freshness_thresholds("weekly")

    def row(age: timedelta):
        return freshness.source_freshness_rows(
            ({
                "source_id": "static",
                "provider": "dkb",
                "label": "DKB",
                "acquisition_mode": "csv",
                "generated_at": (now - age).isoformat(),
            },),
            now=now,
            threshold_hours=24,
            threshold_hours_by_kind=defaults,
        )[0]

    assert row(timedelta(days=4, hours=12))["within_age_threshold"] is True
    assert row(timedelta(days=5))["within_age_threshold"] is True
    assert row(timedelta(days=5, seconds=1))["within_age_threshold"] is False


def test_explicit_static_threshold_still_wins_over_cadence_default() -> None:
    freshness = _freshness_module()
    now = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)
    thresholds = freshness.default_freshness_thresholds("monthly")
    thresholds["csv"] = 48
    rows = freshness.source_freshness_rows(
        ({
            "source_id": "dkb",
            "provider": "dkb",
            "label": "DKB",
            "acquisition_mode": "csv",
            "generated_at": (now - timedelta(hours=49)).isoformat(),
        },),
        now=now,
        threshold_hours=24,
        threshold_hours_by_kind=thresholds,
    )
    assert rows[0]["threshold_hours"] == 48
    assert rows[0]["within_age_threshold"] is False


def test_runtime_wiring_preserves_explicit_options_and_exposes_csv_alias() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    assert '"csv": csv_threshold' in coordinator
    assert 'entry.options.get(CONF_FRESHNESS_CSV_HOURS)' in coordinator
    assert 'entry.options.get(CONF_FRESHNESS_STATEMENT_HOURS)' in coordinator
    assert "default_freshness_thresholds(" in coordinator
    assert "default_freshness_thresholds(" in flow
    assert 'options.get(CONF_FRESHNESS_CSV_HOURS, defaults["csv"])' in flow
    assert 'options.get(CONF_FRESHNESS_STATEMENT_HOURS, defaults["imported_statement"])' in flow
