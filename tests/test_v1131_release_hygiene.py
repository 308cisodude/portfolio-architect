"""v1.13.1 release-hygiene contracts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "dashboard"
WITHDRAWN_SOURCE_NAME = "allocation-overview-markdown.yaml"
WITHDRAWN_ARTIFACT_FRAGMENT = "allocation-overview-card"


def test_withdrawn_markdown_card_sources_are_absent() -> None:
    assert not (DASHBOARD / WITHDRAWN_SOURCE_NAME).exists()
    for locale in ("en", "de"):
        assert not (DASHBOARD / locale / WITHDRAWN_SOURCE_NAME).exists()


def test_reference_dashboard_does_not_render_the_aggregate_overview() -> None:
    for path in DASHBOARD.rglob("*.yaml"):
        source = path.read_text(encoding="utf-8")
        assert "sensor.portfolio_architect_allocation_overview" not in source, path
        if "type: markdown" in source.casefold():
            assert "sensor.portfolio_architect_execution_path" in source, path


def test_release_tooling_cannot_republish_withdrawn_card_artifacts() -> None:
    build = (ROOT / "tools/build_release.py").read_text(encoding="utf-8")
    verify = (ROOT / "tools/verify_release.py").read_text(encoding="utf-8")
    assert WITHDRAWN_SOURCE_NAME not in build
    assert WITHDRAWN_ARTIFACT_FRAGMENT not in build
    assert WITHDRAWN_ARTIFACT_FRAGMENT not in verify
