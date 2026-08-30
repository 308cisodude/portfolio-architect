from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_v1590_all_official_ingress_pages_render_read_only_authority_status() -> None:
    targets = (
        "gateway/src/portfolio_architect_gateway/app.py",
        "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway/dkb_app.py",
        "home_assistant_app/portfolio_architect_gateway_trade_republic/src/portfolio_architect_gateway/trade_republic_app.py",
        "home_assistant_app/portfolio_architect_gateway_import/src/portfolio_architect_gateway/generic_import_app.py",
    )
    for target in targets:
        source = _read(target)
        assert "render_acquisition_authority" in source
        assert "ACQUISITION_AUTHORITY_CSS" in source
        assert "authority_html" in source


def test_v1590_presentation_helper_is_common_synced_source_and_has_no_control_endpoint() -> None:
    helper = _read("gateway/src/portfolio_architect_gateway/acquisition_presentation.py")
    sync = _read("tools/sync_gateway_app_sources.py")

    assert '"acquisition_presentation.py"' in sync
    assert "Read-only capability authority and method readiness" in helper
    assert "Automatic fallback remains disabled" in helper
    assert "Can activate:" in helper
    assert "<form" not in helper
    assert "<button" not in helper
    assert "set-acquisition" not in helper


def test_v1590_does_not_advance_wire_schemas_or_dkb_fints_gate() -> None:
    server = _read("gateway/src/portfolio_architect_gateway/server.py")
    rest_client = _read("custom_components/portfolio_architect/rest_client.py")
    dkb = _read(
        "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway/dkb_csv.py"
    )

    assert 'HEALTH_V9_MEDIA_TYPE = "application/vnd.portfolio-architect.health+json;version=9"' in server
    assert "min(version, 9)" in server
    assert '"requested_health_schema_version": 9' in rest_client
    assert 'AcquisitionMethod("fints", METHOD_RESEARCH_ONLY, False, False)' in dkb
