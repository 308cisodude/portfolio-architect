"""Regression coverage for v1.60 capability evidence observability."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_v1600_all_official_ingress_pages_bind_authority_to_canonical_evidence_clocks() -> None:
    targets = (
        "gateway/src/portfolio_architect_gateway/app.py",
        "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway/dkb_app.py",
        "home_assistant_app/portfolio_architect_gateway_trade_republic/src/portfolio_architect_gateway/trade_republic_app.py",
        "home_assistant_app/portfolio_architect_gateway_import/src/portfolio_architect_gateway/generic_import_app.py",
    )
    for target in targets:
        source = _read(target)
        assert "render_acquisition_authority" in source
        assert "capability_evidence_timestamps()" in source


def test_v1600_common_gateway_evidence_helper_is_read_only_and_snapshot_scoped() -> None:
    server = _read("gateway/src/portfolio_architect_gateway/server.py")
    presentation = _read("gateway/src/portfolio_architect_gateway/acquisition_presentation.py")

    assert "def capability_evidence_timestamps" in server
    assert "already-published canonical Gateway snapshot" in server
    assert "Inactive staged provider evidence is deliberately excluded" in server
    assert "Authoritative evidence" in presentation
    assert "Evidence timestamp" in presentation
    assert "inactive staged evidence" in presentation
    assert "<form" not in presentation
    assert "<button" not in presentation
    assert "set-acquisition" not in presentation


def test_v1600_keeps_health_schema9_and_dkb_research_gate_unchanged() -> None:
    server = _read("gateway/src/portfolio_architect_gateway/server.py")
    rest_client = _read("custom_components/portfolio_architect/rest_client.py")
    dkb = _read(
        "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway/dkb_csv.py"
    )

    assert 'HEALTH_V9_MEDIA_TYPE = "application/vnd.portfolio-architect.health+json;version=9"' in server
    assert "min(version, 9)" in server
    assert '"requested_health_schema_version": 9' in rest_client
    assert 'AcquisitionMethod("fints", METHOD_RESEARCH_ONLY, False, False)' in dkb
