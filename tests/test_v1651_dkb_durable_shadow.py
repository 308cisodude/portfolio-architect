"""Manual FinTS shadow persistence and failure boundaries, with no bank request."""
from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

from test_v1641_dkb_holdings_research import modules


def test_complete_manual_result_survives_restart_but_transient_detail_expires(tmp_path):
    _, app = modules()
    shadow = importlib.import_module(f"{app.__package__}.dkb_shadow")
    review = importlib.import_module(f"{app.__package__}.dkb_holdings_review")
    research = importlib.import_module(f"{app.__package__}.dkb_holdings_research")
    controller = app.DKBProbeController(tmp_path)
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    row = review.ReviewRow("IE00BJ0KDQ92", "2.0", "281.97", "EUR", "unavailable",
                           instrument_line="ISIN IE00BJ0KDQ92|Private bank description")
    result = research.HoldingsObservation(observed, "retrieved", 1, 1)
    controller._capture_review([(row,)], None, result)
    assert controller.holdings_review() is not None
    stored = controller.shadow_file.read_text()
    assert "Private bank description" not in stored
    assert "IE00BJ0KDQ92" in stored
    assert shadow.shadow_summary(controller.shadow_file)["state"] == "fresh"
    restarted = app.DKBProbeController(tmp_path)
    assert restarted.holdings_review() is None
    assert shadow.shadow_summary(restarted.shadow_file)["position_count"] == 1
    restarted._capture_review([(review.ReviewRow("unavailable", "2", "3", "EUR", "unavailable"),)], None, result)
    assert restarted.shadow_file.read_text() == stored
    assert shadow.shadow_summary(controller.shadow_file, datetime.now(timezone.utc) + timedelta(hours=25))["state"] == "stale"


def test_shadow_rejects_duplicate_partial_future_and_corrupt_state(tmp_path):
    _, app = modules()
    shadow = importlib.import_module(f"{app.__package__}.dkb_shadow")
    review = importlib.import_module(f"{app.__package__}.dkb_holdings_review")
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    row = review.ReviewRow("IE00BJ0KDQ92", "2", "281.97", "EUR", "unavailable")
    assert shadow.project_shadow((row, row), observed) is None
    assert shadow.project_shadow((review.ReviewRow("IE00BJ0KDQ92", "2", "281.97", "unavailable", "unavailable"),), observed) is None
    assert shadow.project_shadow((row,), (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()) is None
    path = tmp_path / "shadow.json"
    path.write_text('{"positions": ["bad"]}')
    assert shadow.shadow_summary(path)["state"] == "invalid"
    assert shadow.shadow_summary(tmp_path / "missing.json")["state"] == "absent"


def test_product_registration_change_clears_durable_shadow(tmp_path):
    _, app = modules()
    shadow = importlib.import_module(f"{app.__package__}.dkb_shadow")
    controller = app.DKBProbeController(tmp_path)
    shadow.save_shadow(controller.shadow_file, {"schema_version": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "positions": []})
    controller.configure_product_id("9FA6681DEC0CF3046BFC2F8A6")
    assert not controller.shadow_file.exists()
