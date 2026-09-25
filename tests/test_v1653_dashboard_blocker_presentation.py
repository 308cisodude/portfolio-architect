"""Visible blocker evidence must remain in generated native dashboard cards."""

from pathlib import Path


import yaml

ROOT = Path(__file__).resolve().parents[1]


def _cards(locale: str, section: int):
    return yaml.safe_load((ROOT / "dashboard/generated" / f"portfolio-architect-dashboard-{locale}.yaml").read_text())["views"][0]["sections"][section]["cards"]


def test_source_blocker_and_no_purchase_are_distinct() -> None:
    for locale in ("en", "de"):
        cards = _cards(locale, 0)
        blocker = next(card for card in cards if card.get("card", {}).get("type") == "markdown" and "plan_actionability_detail" in card["card"].get("content", ""))
        assert blocker["conditions"] == [{"condition": "state", "entity": "sensor.portfolio_architect_plan_actionability", "state": "not_actionable"}]
        for state in ("no_eligible_purchase", "reserve_unavailable", "deferred_for_cost_efficiency"):
            card = next(card for card in cards if card.get("card", {}).get("type") == "markdown" and any(c.get("state") == state for c in card["conditions"]))
            assert {c.get("state") for c in card["conditions"]} == {state, "not_ready"}
            assert card["card"]["content"]


def test_findings_show_specific_route_evidence_without_entity_popup() -> None:
    for locale in ("en", "de"):
        card = next(card for card in _cards(locale, 1) if card.get("type") == "markdown")
        content = card["content"]
        assert "finding.fund_name" in content
        assert "finding.observed" in content and "finding.expected" in content
        assert 'finding.state == "error"' in content
        assert ("Sparplanweg erforderlich" if locale == "de" else "Savings plan route required") in content
        assert "presentation_model" in card["entity_id"]


def test_two_stale_sources_are_both_named_in_plan_summary() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("pa_freshness", ROOT / "custom_components/portfolio_architect/freshness.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    blockers = [
        {"label": label, "timestamp_status": "ok", "age_seconds": 15 * 86400, "threshold_hours": 336}
        for label in ("DKB cash CSV", "Trade Republic portfolio statement")
    ]
    for german in (False, True):
        summary = module.stale_summary(blockers, german=german)
        assert "DKB cash CSV" in summary
        assert "Trade Republic portfolio statement" in summary
        assert len(summary) <= 240
